"""Lectura verificada de una ejecución terminada, sin generar datos ni ajustar ML."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import CONFIG, CSV_COLUMNS, GATEWAYS
from detection import ChangeDetector, DetectionConfig
from morris import GatewayMorris
from simulator import SecurityEvent
from storage import RunPaths, check_manifest
from validation import compare_nested, require, validate_projection, validate_raw


class ReviewedRun:
    def __init__(self, root: Path):
        self.output_dir = Path(root)
        self.paths = RunPaths(self.output_dir)
        self.config = CONFIG
        self.manifest = check_manifest(self.paths)
        self._raw = validate_raw(self.paths.data)
        self.summary = json.loads((self.paths.results / "resumen_defensa.json").read_text(encoding="utf-8"))
        self.ml_real = bool(self.manifest["ml_real"])
        require(self.ml_real, "El modo revisión requiere una ejecución completa con UMAP y K-means reales")
        self.model_metadata = json.loads((self.paths.models / "metadatos.json").read_text(encoding="utf-8"))
        self._points = pd.read_csv(self.paths.results / "eventos_proyectados.csv")
        validate_projection(self._points, self._raw)
        model = self.model_metadata
        require(model["ids_entrenamiento"] == list(range(1, 301)), "ID de entrenamiento incorrectos")
        require(model["variables"] == list(CSV_COLUMNS[3:7]), "Variables de aprendizaje incorrectas")
        require((model["eventos_entrenamiento"], model["eventos_transformados"], model["eventos_procesados"]) == (300, 5700, 6000), "Recuentos de ML incorrectos")
        require(model["lotes_transformados"] == [100]*57, "Inferencia fuera de los lotes oficiales")
        self.centroids = np.asarray(model["centroides"], dtype=float)
        require(self.centroids.shape == (3, 2) and np.isfinite(self.centroids).all(), "Centroides inválidos")
        nearest = ((self._points[["umap_x", "umap_y"]].to_numpy()[:, None, :] - self.centroids)**2).sum(axis=2).argmin(axis=1)
        require(np.array_equal(nearest, self._points.cluster), "Asignaciones distintas al centroide más cercano")
        self.event_count = 6000
        self.is_finished = True
        self.finalized = True
        self.failed = False
        self.morris = GatewayMorris()
        self.detector = ChangeDetector(DetectionConfig(**self.summary["deteccion"]["configuracion"]))
        expected_history = []
        totals = dict.fromkeys(GATEWAYS, 0)
        for record in self._raw.to_dict(orient="records"):
            event = SecurityEvent(**record)
            self.morris.update(event.pasarela, event.fallos)
            self.detector.update(event)
            totals[event.pasarela] += event.fallos
            if event.id >= 300 and event.id % 100 == 0:
                expected_history.append({"eventos": event.id, "instante": event.instante,
                                         **{f"real_{g}": totals[g] for g in GATEWAYS},
                                         **{f"morris_{g}": self.morris.estimate(g) for g in GATEWAYS}})
        history = pd.read_csv(self.paths.results / "evolucion_morris.csv")
        try:
            pd.testing.assert_frame_equal(history, pd.DataFrame(expected_history), check_dtype=False)
            recorded = pd.read_csv(self.paths.results / "evolucion_cambios.csv")
            pd.testing.assert_frame_equal(recorded, pd.DataFrame(self.detector.history), check_dtype=False)
        except AssertionError as exc:
            raise ValueError("Historial incompatible con los eventos observados") from exc
        self.history = expected_history
        from report import calculate_defense
        compare_nested(self.summary, calculate_defense(self))

    def snapshot(self) -> pd.DataFrame:
        return self._points.copy()

    def from_csv(self) -> pd.DataFrame:
        return self._raw.copy()
