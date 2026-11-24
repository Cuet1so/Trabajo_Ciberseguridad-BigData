"""Contratos de presentación frente a los datos del experimento real."""
import numpy as np
import pandas as pd
import pytest

import bi_charts as charts
from bi_metrics import build_dashboard_data, filter_points, number


def test_summary_and_bars_match_csv_period_means(real_run):
    exp, _ = real_run
    raw, points = exp.from_csv(), exp.snapshot()
    data = build_dashboard_data(raw, points)
    assert data.comparison_ready
    differences = {}
    for metric, column in (("cuentas_medias", "cuentas"), ("fallos_medios", "fallos"), ("ips_medias", "ips_origen")):
        fig = charts.before_after(data.periods, metric, column)
        for gateway in ("Ámbar", "Cobalto"):
            subset = raw[raw.pasarela == gateway]
            before = subset.loc[subset.id <= 3000, column].mean()
            after = subset.loc[subset.id > 3000, column].mean()
            change = data.change(gateway, metric)
            assert change.before == pytest.approx(before)
            assert change.after == pytest.approx(after)
            assert change.difference == pytest.approx(after-before)
            assert change.percentage == pytest.approx(100*(after-before)/before)
            trace = next(t for t in fig.data if t.name == gateway)
            np.testing.assert_allclose(trace.y, [before, after])
            if metric == "cuentas_medias":
                differences[gateway] = after-before
        assert fig.layout.yaxis.range[0] == 0
    assert data.accounts_did == pytest.approx(differences["Cobalto"]-differences["Ámbar"])


def test_incomplete_periods_cannot_produce_final_conclusion(real_run):
    exp, _ = real_run
    for size in (300, 3000, 5900):
        data = build_dashboard_data(exp.from_csv().head(size), exp.snapshot().head(size))
        assert not data.comparison_ready
        with pytest.raises(ValueError, match="1500"):
            data.change("Cobalto", "cuentas_medias")


def test_map_keeps_coordinates_centroids_and_scale_when_filtered(real_run):
    exp, _ = real_run
    points = exp.snapshot()
    unchanged = points.copy(deep=True)
    complete = charts.umap_map(points, points, exp.centroids, [0, 1, 2])
    selected = filter_points(points, "Cobalto", "Segunda mitad", [2])
    filtered = charts.umap_map(selected, points, exp.centroids, [2])
    assert filtered.layout.xaxis.range == complete.layout.xaxis.range
    assert filtered.layout.yaxis.range == complete.layout.yaxis.range
    traces = {trace.name: trace for trace in filtered.data}
    np.testing.assert_array_equal(traces["Grupo 2"].x, selected.umap_x)
    np.testing.assert_array_equal(traces["Grupo 2"].y, selected.umap_y)
    np.testing.assert_array_equal(traces["Grupo 2"].customdata[:, 0], selected.id)
    np.testing.assert_allclose([traces["Centroide 2"].x[0], traces["Centroide 2"].y[0]], exp.centroids[2])
    all_event_traces = [trace for trace in complete.data if trace.customdata is not None]
    assert sum(len(trace.x) for trace in all_event_traces) == 6000
    assert sum((trace.customdata[:, 7] == "Ajuste inicial").sum() for trace in all_event_traces) == 300
    pd.testing.assert_frame_equal(points, unchanged)


def test_group_percentages_and_heatmap_preserve_actual_counts(real_run):
    exp, _ = real_run
    points = exp.snapshot()
    data = build_dashboard_data(exp.from_csv(), points)
    distribution = charts.group_distribution(data.periods)
    np.testing.assert_allclose(np.array([trace.x for trace in distribution.data]).sum(axis=0), 100)
    for i, row in enumerate(data.periods.itertuples()):
        period = points[points.id.le(3000) if row.mitad.startswith("Antes") else points.id.gt(3000)]
        subset = period[period.pasarela == row.pasarela]
        assert len(subset) == 1500
        for group in range(3):
            assert distribution.data[group].x[i] == pytest.approx(100*subset.cluster.eq(group).mean())
    heatmap = charts.profile_heatmap(data.correspondence)
    expected = pd.crosstab(points.cluster, points.perfil, normalize="index")*100
    expected = expected.reindex(index=data.correspondence.index, columns=data.correspondence.columns)
    np.testing.assert_allclose(heatmap.data[0].z, expected.to_numpy())


def test_morris_charts_retain_exact_totals_and_handle_zero(real_run):
    exp, _ = real_run
    history = pd.DataFrame(exp.history)
    volume = charts.morris_evolution(history)
    error = charts.morris_error(history)
    for index, gateway in enumerate(("Ámbar", "Cobalto")):
        exact = exp.from_csv().loc[lambda frame: frame.pasarela == gateway, "fallos"].sum()
        assert volume.data[index*2].y[-1] == exact
        assert volume.data[index*2+1].y[-1] == exp.morris.estimate(gateway)
        assert error.data[index].y[-1] == pytest.approx(100*abs(exp.morris.estimate(gateway)-exact)/exact)
    empty_start = history.iloc[:1].copy()
    for column in empty_start.columns:
        if column.startswith(("real_", "morris_")):
            empty_start[column] = 0
    assert all(trace.y[0] == 0 for trace in charts.morris_error(empty_start).data)


def test_spanish_number_format_is_unambiguous():
    assert number(97440) == "97.440"
    assert number(13.9513333, 3, signed=True) == "+13,951"
    assert number(-.2426666, 3, signed=True) == "-0,243"
    assert number(-.00001, 2) == "0,00"
    assert number(float("nan")) == "—"
