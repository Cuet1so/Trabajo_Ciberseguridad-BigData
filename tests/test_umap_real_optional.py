"""Prueba real opcional: se ejecuta al instalar umap-learn en el equipo local."""
import pytest

from analytics import FixedUMAPClusters
from simulator import generate_events


def test_umap_real_fit_first_300_and_transform_next_100():
    pytest.importorskip("umap", reason="Instalar umap-learn para ejecutar la prueba real")
    events=list(generate_events())[:400]
    model=FixedUMAPClusters()
    initial, groups=model.fit_initial(events[:300])
    assert initial.shape == (300,2)
    assert len(set(groups.tolist())) == 3
    future, labels=model.transform_new(events[300:400])
    assert future.shape == (100,2)
    assert labels.shape == (100,)
    assert set(labels.tolist()).issubset({0,1,2})
