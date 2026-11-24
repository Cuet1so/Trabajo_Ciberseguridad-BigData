"""Fixture de integración con implementaciones reales y observadores de llamadas."""
from __future__ import annotations

import numpy as np
import pytest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from pipeline import StreamingExperiment


@pytest.fixture(scope="session")
def real_run(tmp_path_factory):
    import umap

    directory = tmp_path_factory.mktemp("real_6000")
    calls = {"scaler_fit": [], "umap_fit": [], "kmeans_fit": [], "transform": [], "predict": []}
    patch = pytest.MonkeyPatch()

    def observe(cls, method, key):
        original = getattr(cls, method)

        def wrapped(self, values, *args, **kwargs):
            calls[key].append(np.array(values, copy=True))
            return original(self, values, *args, **kwargs)

        patch.setattr(cls, method, wrapped)

    observe(StandardScaler, "fit", "scaler_fit")
    observe(umap.UMAP, "fit", "umap_fit")
    observe(KMeans, "fit", "kmeans_fit")
    observe(umap.UMAP, "transform", "transform")
    observe(KMeans, "predict", "predict")
    try:
        with StreamingExperiment(directory) as exp:
            exp.step()
            initial_centers = exp.centroids.copy()
            initial_mean = exp.projector.scaler.mean_.copy()
            initial_embedding = exp.projector.reducer.embedding_.copy()
            exp.run_to_end()
            assert np.array_equal(exp.centroids, initial_centers)
            assert np.array_equal(exp.projector.scaler.mean_, initial_mean)
            assert np.array_equal(exp.projector.reducer.embedding_, initial_embedding)
    finally:
        patch.undo()
    return exp, calls
