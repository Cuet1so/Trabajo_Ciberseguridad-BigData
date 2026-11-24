"""Proyección UMAP fija en los primeros 300 eventos + K-means (k=3)."""
from __future__ import annotations

from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from config import CONFIG, FEATURE_COLUMNS, ExperimentConfig
from simulator import SecurityEvent
from storage import versions, write_json


class FixedUMAPClusters:
    def __init__(self, config: ExperimentConfig = CONFIG):
        self.config = config
        self.scaler: StandardScaler | None = None
        self.reducer: Any = None  # Importación diferida: el modo diagnóstico no necesita UMAP.
        self.kmeans: KMeans | None = None
        self.training_ids: list[int] = []
        self.transformed_events = 0
        self.transform_batches: list[int] = []

    def fit_initial(self, events: Sequence[SecurityEvent]) -> tuple[np.ndarray, np.ndarray]:
        if self.scaler is not None:
            raise RuntimeError("Los modelos ya están ajustados; no se permite reentrenar")
        if [e.id for e in events] != list(range(1, self.config.initial_training_events + 1)):
            raise ValueError("Es obligatorio ajustar exclusivamente los primeros 300 eventos")
        try:
            import umap  # pip install umap-learn
        except ImportError as exc:
            raise RuntimeError("Falta umap-learn: instala 'pip install -r requirements.txt'") from exc

        array = np.asarray([event.features() for event in events], dtype=np.float64)
        self.scaler = StandardScaler().fit(array)
        standardized = self.scaler.transform(array)
        self.reducer = umap.UMAP(
            n_components=2,
            n_neighbors=15,
            min_dist=0.10,
            metric="euclidean",
            random_state=self.config.umap_seed,
            transform_seed=self.config.umap_seed,
            n_jobs=1,
        )
        coords = np.asarray(self.reducer.fit_transform(standardized), dtype=np.float64)
        self.kmeans = KMeans(n_clusters=3, n_init=20, random_state=self.config.kmeans_seed)
        labels = self.kmeans.fit_predict(coords)
        self.training_ids = [e.id for e in events]
        self._check(coords, labels, len(events))
        return coords, np.asarray(labels, dtype=np.int64)

    def transform_new(self, events: Sequence[SecurityEvent]) -> tuple[np.ndarray, np.ndarray]:
        if self.scaler is None or self.reducer is None or self.kmeans is None:
            raise RuntimeError("Es necesario ajustar los primeros 300 eventos")
        if not events:
            return np.empty((0, 2)), np.empty(0, dtype=int)
        if any(e.id <= self.config.initial_training_events for e in events):
            raise ValueError("transform_new solo admite eventos posteriores al entrenamiento")
        array = np.asarray([event.features() for event in events], dtype=np.float64)
        coords = np.asarray(self.reducer.transform(self.scaler.transform(array)), dtype=np.float64)
        # Los centroides NO se vuelven a ajustar: únicamente predecimos.
        labels = np.asarray(self.kmeans.predict(coords), dtype=np.int64)
        self._check(coords, labels, len(events))
        self.transformed_events += len(events)
        self.transform_batches.append(len(events))
        return coords, labels

    @staticmethod
    def _check(coords: np.ndarray, labels: np.ndarray, count: int) -> None:
        if coords.shape != (count, 2) or not np.isfinite(coords).all():
            raise ValueError("UMAP produjo coordenadas inválidas")
        if labels.shape != (count,) or not np.isin(labels, [0, 1, 2]).all():
            raise ValueError("K-means produjo etiquetas inválidas")

    def metadata(self) -> dict[str, Any]:
        if self.scaler is None or self.reducer is None or self.kmeans is None:
            raise RuntimeError("No hay modelos ajustados")
        return {
            "variables": list(FEATURE_COLUMNS), "ids_entrenamiento": self.training_ids,
            "eventos_entrenamiento": len(self.training_ids),
            "eventos_transformados": self.transformed_events,
            "lotes_transformados": self.transform_batches.copy(),
            "eventos_procesados": len(self.training_ids) + self.transformed_events,
            "semillas": {"simulador": self.config.simulator_seed, "morris": self.config.morris_seed,
                         "umap": self.config.umap_seed, "transform": self.config.umap_seed,
                         "kmeans": self.config.kmeans_seed},
            "versiones": versions(),
            "parametros": json.loads(json.dumps({"scaler": self.scaler.get_params(), "umap": self.reducer.get_params(),
                           "kmeans": self.kmeans.get_params()})),
            "centroides": self.kmeans.cluster_centers_.tolist(),
        }

    def save(self, directory: Path) -> None:
        metadata = self.metadata()
        directory.mkdir(parents=True, exist_ok=True)
        for name, model in (("scaler", self.scaler), ("umap", self.reducer), ("kmeans", self.kmeans)):
            temporary = directory / f"{name}.joblib.tmp"
            joblib.dump(model, temporary, compress=3)
            temporary.replace(directory / f"{name}.joblib")
        write_json(directory / "metadatos.json", metadata)

    @classmethod
    def load(cls, run_dir: Path, *, trusted_local: bool = False) -> "FixedUMAPClusters":
        """Solo artefactos locales de confianza: joblib puede ejecutar código al cargar.

        SHA256 detecta corrupción accidental, no autentica a un autor externo.
        El dashboard de revisión usa JSON/CSV; no deserializa joblib.
        """
        import json
        from storage import RunPaths, check_manifest

        if not trusted_local:
            raise ValueError("Solo se permite cargar modelos locales de confianza")
        paths = RunPaths(Path(run_dir))
        manifest = check_manifest(paths)
        if not manifest.get("ml_real"):
            raise ValueError("Esta ejecución no contiene modelos reales")
        metadata = json.loads((paths.models / "metadatos.json").read_text(encoding="utf-8"))
        current = versions()
        for name, old in metadata["versiones"].items():
            if current.get(name) != old:
                raise ValueError(f"Versión incompatible de {name}: {current.get(name)} frente a {old}")
        model = cls()
        model.scaler = joblib.load(paths.models / "scaler.joblib")
        model.reducer = joblib.load(paths.models / "umap.joblib")
        model.kmeans = joblib.load(paths.models / "kmeans.joblib")
        model.training_ids = metadata["ids_entrenamiento"]
        model.transformed_events = metadata["eventos_transformados"]
        model.transform_batches = metadata["lotes_transformados"]
        return model
