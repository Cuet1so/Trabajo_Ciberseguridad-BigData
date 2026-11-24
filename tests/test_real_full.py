"""Evidencia obligatoria para los cinco criterios, con UMAP y sklearn reales."""
import json

import numpy as np
import pandas as pd
import pytest
from pypdf import PdfReader

from config import FEATURE_COLUMNS, GATEWAYS, PROFILES
from report import calculate_defense, comparison_table, cluster_characterization
from verificar import validate


def test_real_6000_single_training_no_future_refit(real_run):
    exp, calls = real_run
    raw = exp.from_csv()
    assert len(raw) == 6000
    assert raw.groupby("pasarela").size().to_dict() == {"Ámbar": 3000, "Cobalto": 3000}
    assert [row["eventos"] for row in exp.history] == list(range(300, 6001, 100))
    assert len(calls["scaler_fit"]) == len(calls["umap_fit"]) == len(calls["kmeans_fit"]) == 1
    features = raw.loc[:299, list(FEATURE_COLUMNS)].to_numpy(dtype=float)
    assert calls["scaler_fit"][0].shape == (300, 4)
    np.testing.assert_array_equal(calls["scaler_fit"][0], features)
    standardized = exp.projector.scaler.transform(features)
    np.testing.assert_allclose(calls["umap_fit"][0], standardized)
    assert calls["kmeans_fit"][0].shape == (300, 2)
    np.testing.assert_array_equal(calls["kmeans_fit"][0], exp.projector.reducer.embedding_)
    assert [arr.shape for arr in calls["transform"]] == [(100, 4)]*57
    assert [arr.shape for arr in calls["predict"]] == [(100, 2)]*57
    np.testing.assert_allclose(np.concatenate(calls["transform"]), exp.projector.scaler.transform(raw.loc[300:, list(FEATURE_COLUMNS)].to_numpy(dtype=float)))
    points = exp.snapshot()
    assert points[["umap_x", "umap_y"]].shape == (6000, 2)
    assert np.isfinite(points[["umap_x", "umap_y"]]).all().all()
    assert set(points.cluster) == {0, 1, 2}
    assert exp.centroids.shape == (3, 2)
    with pytest.raises(RuntimeError, match="reentrenar"):
        exp.projector.fit_initial([])


def test_real_statistics_csv_dashboard_pdf_agree(real_run):
    exp, _ = real_run
    summary = calculate_defense(exp)
    saved = json.loads((exp.paths.results / "resumen_defensa.json").read_text())
    assert summary == saved
    stats = comparison_table(exp.snapshot())  # Misma función que consume la vista 3.
    assert stats.minutos.tolist() == [1500]*4
    np.testing.assert_allclose(stats[[f"porcentaje_grupo_{i}" for i in range(3)]].sum(axis=1), 100)
    np.testing.assert_allclose(stats[[f"porcentaje_{p}" for p in PROFILES]].sum(axis=1), 100)
    char, cross = cluster_characterization(exp.snapshot())
    assert char.eventos.sum() == 6000
    np.testing.assert_allclose(cross.sum(axis=1), 100)
    text = "\n".join(page.extract_text() for page in PdfReader(exp.paths.results / "Informe_Defensa_Tecnica.pdf").pages)
    for gateway in GATEWAYS:
        values = summary["morris"][gateway]
        assert f"{values['exacto_csv']:,.0f}" in text
        assert f"{values['estimacion_morris']:,.0f}" in text
        assert f"{values['error_relativo_porcentaje']:.2f} %" in text
        assert str(values["registros_finales"]) in text
    assert "13.951" in text and "336.3 %" in text
    assert "32.857" in text and "32.614" in text
    assert "13.981" in text
    assert "5700" in text and "6000" in text
    assert "Correspondencia observada" in text
    assert validate(exp.output_dir, require_ml=True)["ml_real"]
