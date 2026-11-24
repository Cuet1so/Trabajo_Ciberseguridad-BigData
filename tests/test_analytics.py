"""Prueba de contrato de UMAP; no suplanta una ejecución real de umap-learn."""
import sys
import types

import numpy as np
import pytest

from analytics import FixedUMAPClusters
from simulator import generate_events


class DummyUMAP:
    def __init__(self, **kwargs):
        assert kwargs["n_components"] == 2
        self._reference = None

    def fit_transform(self, values):
        self._reference = np.array(values, copy=True)
        return np.asarray(values)[:, :2]

    def transform(self, values):
        assert self._reference is not None
        return np.asarray(values)[:, :2]


def test_scaler_and_umap_fit_once_then_only_transform(monkeypatch):
    monkeypatch.setitem(sys.modules, "umap", types.SimpleNamespace(UMAP=DummyUMAP))
    events = list(generate_events())
    projection = FixedUMAPClusters()
    with pytest.raises(ValueError):
        projection.fit_initial(events[:299])
    initial, labels = projection.fit_initial(events[:300])
    assert initial.shape == (300, 2)
    assert set(labels) == {0, 1, 2}
    means = projection.scaler.mean_.copy()
    future, predicted = projection.transform_new(events[300:400])
    assert future.shape == (100, 2)
    assert predicted.shape == (100,)
    assert np.array_equal(means, projection.scaler.mean_)
    assert projection.kmeans.n_clusters == 3
