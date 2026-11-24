"""Motor compartido por CLI y Streamlit: una ejecución incremental por instancia."""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

from analytics import FixedUMAPClusters
from config import CONFIG, CSV_COLUMNS, GATEWAY_FILES, GATEWAYS, ExperimentConfig
from detection import ChangeDetector, DetectionConfig
from morris import GatewayMorris
from simulator import CSVEventWriter, SecurityEvent, generate_events
from storage import RunLease, RunPaths, seal_run, versions, write_json


class Projector(Protocol):
    def fit_initial(self, events: Sequence[SecurityEvent]) -> tuple[np.ndarray, np.ndarray]: ...
    def transform_new(self, events: Sequence[SecurityEvent]) -> tuple[np.ndarray, np.ndarray]: ...


class StreamingExperiment:
    def __init__(self, output_dir: Path = CONFIG.output_dir, config: ExperimentConfig = CONFIG,
                 *, use_ml: bool = True, projector: Projector | None = None,
                 detection_config: DetectionConfig = DetectionConfig()) -> None:
        self.config = config
        self.output_dir = Path(output_dir)
        self.paths = RunPaths(self.output_dir)
        self._lease = RunLease(self.paths)
        try:
            self.writer = CSVEventWriter(self.paths.data)
            self._source: Iterator[SecurityEvent] = generate_events(config)
            self.morris = GatewayMorris(config)
            self.detector = ChangeDetector(detection_config)
            self.projector: Projector | None = (
                projector if projector is not None else FixedUMAPClusters(config) if use_ml else None
            )
            self.event_count = 0
            self.records: list[dict[str, Any]] = []
            self.exact_running = {gateway: 0 for gateway in GATEWAYS}
            self.history: list[dict[str, Any]] = []
            self._closed = False
            self.failed = False
            self.finalized = False
            write_json(self.paths.manifest, {"schema": 1, "estado": "en_curso", "eventos": 0})
        except Exception:
            self._lease.close()
            raise

    def step(self, number_of_events: int | None = None) -> int:
        if self.failed:
            raise RuntimeError("La ejecución falló. Conserva sus archivos y reiníciala; no se omiten eventos")
        if self.is_finished:
            return 0
        if self._closed:
            raise RuntimeError("La ejecución está cerrada")
        # Incluso step(6000) se detiene en el siguiente punto oficial de actualización.
        target = 300 if self.event_count < 300 else ((self.event_count // 100) + 1) * 100
        requested = target - self.event_count if number_of_events is None else number_of_events
        if isinstance(requested, bool) or not isinstance(requested, int) or requested <= 0:
            raise ValueError("El tamaño de lote debe ser un entero positivo")
        count = min(requested, target - self.event_count, 6000 - self.event_count)
        try:
            batch: list[SecurityEvent] = []
            for _ in range(count):
                event = next(self._source)
                self.writer.write(event)
                self.morris.update(event.pasarela, event.fallos)
                self.detector.update(event)
                self.exact_running[event.pasarela] += event.fallos
                self.records.append(event.as_row())
                batch.append(event)
                self.event_count += 1
            self.writer.flush()
            if self.projector is not None and self.event_count == target:
                if target == 300:
                    initial = [SecurityEvent(**{k: row[k] for k in CSV_COLUMNS}) for row in self.records[:300]]
                    coords, labels = self.projector.fit_initial(initial)
                    self._add_projection(self.records[:300], coords, labels)
                    if isinstance(self.projector, FixedUMAPClusters):
                        self.projector.save(self.paths.models)
                else:
                    pending = [row for row in self.records if "cluster" not in row]
                    events = [SecurityEvent(**{k: row[k] for k in CSV_COLUMNS}) for row in pending]
                    coords, labels = self.projector.transform_new(events)
                    self._add_projection(pending, coords, labels)
            if self.event_count == target:
                self.history.append({
                    "eventos": self.event_count, "instante": self.records[-1]["instante"],
                    **{f"real_{g}": self.exact_running[g] for g in GATEWAYS},
                    **{f"morris_{g}": self.morris.estimate(g) for g in GATEWAYS},
                })
            if self.is_finished:
                self.finalize()
            return count
        except Exception:
            self.failed = True
            self.close()
            raise

    @staticmethod
    def _add_projection(records: Sequence[dict[str, Any]], coords: np.ndarray, labels: np.ndarray) -> None:
        FixedUMAPClusters._check(np.asarray(coords), np.asarray(labels), len(records))
        for rec, xy, label in zip(records, coords, labels, strict=True):
            rec.update(umap_x=float(xy[0]), umap_y=float(xy[1]), cluster=int(label))

    @property
    def is_finished(self) -> bool:
        return self.event_count == self.config.total_events

    @property
    def ml_real(self) -> bool:
        return isinstance(self.projector, FixedUMAPClusters)

    @property
    def model_metadata(self) -> dict[str, Any]:
        return self.projector.metadata() if isinstance(self.projector, FixedUMAPClusters) else {}

    @property
    def centroids(self) -> np.ndarray | None:
        if isinstance(self.projector, FixedUMAPClusters) and self.projector.kmeans is not None:
            return self.projector.kmeans.cluster_centers_.copy()
        return None

    def run_to_end(self) -> None:
        while not self.is_finished:
            self.step()
        self.finalize()

    def from_csv(self) -> pd.DataFrame:
        self.writer.flush()
        frames = [pd.read_csv(self.paths.data / GATEWAY_FILES[g], encoding="utf-8") for g in GATEWAYS]
        return pd.concat(frames, ignore_index=True).sort_values("id").reset_index(drop=True)

    def snapshot(self) -> pd.DataFrame:
        return pd.DataFrame(self.records)

    def save_derived(self) -> None:
        if not self.is_finished:
            raise RuntimeError("No se exportan resultados finales antes de los 6000 eventos")
        if self.finalized:
            return
        self.writer.flush()
        name = "eventos_proyectados.csv" if self.projector is not None else "eventos_sin_proyectar.csv"
        self.snapshot().to_csv(self.paths.results / name, index=False)
        pd.DataFrame(self.history).to_csv(self.paths.results / "evolucion_morris.csv", index=False)
        pd.DataFrame(self.detector.history).to_csv(self.paths.results / "evolucion_cambios.csv", index=False)

    def finalize(self) -> None:
        if self.finalized:
            return
        if not self.is_finished:
            raise RuntimeError("Solo se finalizan ejecuciones completas")
        from pdf_report import build_defense_pdf
        from report import calculate_defense, export_defense
        from validation import validate_raw, validate_projection

        self.save_derived()
        raw = validate_raw(self.paths.data)
        if self.projector is not None:
            validate_projection(self.snapshot(), raw)
        if isinstance(self.projector, FixedUMAPClusters):
            self.projector.save(self.paths.models)
        summary = calculate_defense(self)
        export_defense(self, summary)
        build_defense_pdf(summary, self.paths.results / "Informe_Defensa_Tecnica.pdf")
        seal_run(self.paths, {"eventos": self.event_count, "ml_real": isinstance(self.projector, FixedUMAPClusters),
                              "versiones": versions(), "semilla_simulador": self.config.simulator_seed})
        self.finalized = True
        self.close()

    def close(self) -> None:
        if not self._closed:
            self.writer.close()
            self._lease.close()
            self._closed = True

    def __enter__(self) -> "StreamingExperiment":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
