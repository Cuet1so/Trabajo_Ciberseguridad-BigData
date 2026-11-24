from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from config import CONFIG
from morris import GatewayMorris, Morris8
from pipeline import StreamingExperiment
from simulator import SecurityEvent


def test_morris_zero_positive_and_deterministic():
    a, b = GatewayMorris(), GatewayMorris()
    for sample in [("Ámbar", 42), ("Cobalto", 45), ("Ámbar", 17)]:
        a.update(*sample)
        b.update(*sample)
    assert a.counters["Ámbar"].registers == b.counters["Ámbar"].registers
    assert a.estimate("Ámbar") >= 0
    assert GatewayMorris().estimate("Cobalto") == 0.0
    with pytest.raises(ValueError):
        a.update("Ámbar", -5)


class StubProjector:
    """Double de prueba del contrato, NO sustituye UMAP en la aplicación."""
    def __init__(self):
        self.fit_ids = []
        self.future_ids = []

    def fit_initial(self, events):
        self.fit_ids = [event.id for event in events]
        return np.array([[event.fallos,event.cuentas] for event in events],dtype=float), np.zeros(len(events), dtype=int)

    def transform_new(self, events):
        self.future_ids.extend(event.id for event in events)
        return np.array([[event.fallos,event.cuentas] for event in events],dtype=float), np.ones(len(events), dtype=int)


def test_full_stream_contract_and_csv_truth(tmp_path: Path):
    stub = StubProjector()
    with StreamingExperiment(output_dir=tmp_path, projector=stub) as app:
        app.step()  # Los 300 primeros.
        assert app.event_count == 300
        assert stub.fit_ids == list(range(1, 301))
        assert (app.snapshot().cluster == 0).all()
        app.step(100)
        assert stub.future_ids == list(range(301,401))
        app.run_to_end()
        assert app.is_finished
        assert len(app.from_csv()) == 6000
        assert (app.snapshot().cluster.iloc[300:] == 1).all()
        assert len(stub.future_ids) == 5700
        assert len(pd.read_csv(tmp_path/"datos"/"ambar.csv")) == 3000
        assert len(pd.read_csv(tmp_path/"datos"/"cobalto.csv")) == 3000
        for gw in ("Ámbar","Cobalto"):
            csv_exact = int(app.from_csv().query("pasarela == @gw").fallos.sum())
            assert csv_exact == app.exact_running[gw]
