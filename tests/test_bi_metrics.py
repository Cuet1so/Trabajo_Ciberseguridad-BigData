"""Regresiones BI sobre medidas de los eventos observados."""
from __future__ import annotations

import pandas as pd
import pytest

from bi_metrics import evolution_by_gateway, gateway_kpis
from simulator import generate_events


def test_kpis_use_received_events_only():
    items = [e.as_row() for e in list(generate_events())[:4]]
    result = gateway_kpis(pd.DataFrame(items))
    assert result["Ámbar"]["resumenes"] == 2
    assert result["Cobalto"]["resumenes"] == 2
    assert sum(r["fallos"] for r in result.values()) == sum(x["fallos"] for x in items)
    assert result["Ámbar"]["cuentas_medias"] == pytest.approx((items[0]["cuentas"] + items[2]["cuentas"]) / 2)


def test_evolution_bins_are_minutes_per_gateway():
    events = [e.as_row() for e in list(generate_events())[:202]]
    trend = evolution_by_gateway(pd.DataFrame(events), minutes_per_bin=100)
    assert len(trend) == 4
    for gateway in ("Ámbar", "Cobalto"):
        subset = trend[trend.pasarela == gateway].reset_index(drop=True)
        assert subset.resumenes.tolist() == [100, 1]
        assert subset.minuto_fin.tolist() == [100, 101]
        assert subset.cuentas_medias.notna().all()
    with pytest.raises(ValueError):
        evolution_by_gateway(pd.DataFrame(events).drop(columns="cuentas"))
    with pytest.raises(ValueError):
        evolution_by_gateway(pd.DataFrame(events), minutes_per_bin=0)
