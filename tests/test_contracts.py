from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

import simulator
from config import CONFIG, DISTRIBUTIONS, FEATURE_COLUMNS, GATEWAYS, PROFILE_RANGES, PROFILES
from morris import Morris8, GatewayMorris
from report import morris_metrics
from simulator import CSVEventWriter, generate_events
from validation import validate_raw, validate_projection


def test_exact_generation_probabilities_and_uniform_endpoints(monkeypatch):
    calls = []
    bounds = []

    class ObservedRNG:
        def choice(self, profiles, p):
            calls.append(tuple(p))
            return profiles[(len(calls)-1) % 3]

        def integers(self, low, high):
            bounds.append((low, high))
            return low if len(calls) % 2 else high-1

    monkeypatch.setattr(simulator.np.random, "default_rng", lambda seed: ObservedRNG())
    events = list(generate_events())
    for event, probabilities in zip(events, calls, strict=True):
        expected = DISTRIBUTIONS["cobalto_despues"] if event.id > 3000 and event.pasarela == "Cobalto" else DISTRIBUTIONS["normal"]
        assert probabilities == expected
        for column, (lo, hi), passed in zip(FEATURE_COLUMNS, PROFILE_RANGES[event.perfil], bounds[(event.id-1)*4:event.id*4], strict=True):
            assert passed == (lo, hi+1)
            assert getattr(event, column) == (lo if event.id % 2 else hi)


def test_morris_all_logical_increments_strict_probability_and_mean():
    class RNG:
        calls = 0
        value = .5

        def random(self):
            self.calls += 1
            return self.value

    rng = RNG()
    counter = Morris8(rng)
    assert counter.registers == [0]*8
    counter.update(1)
    assert counter.registers == [1]*8  # .5 < 1
    counter.update(1)
    assert counter.registers == [1]*8  # .5 == 2^-1: comparación estricta.
    rng.value = np.nextafter(.5, 0)
    counter.update(1)
    assert counter.registers == [2]*8
    assert rng.calls == 24
    counter.registers = list(range(8))
    assert counter.estimate == sum(2**c-1 for c in range(8))/8
    for invalid in (-1, 1.5, True):
        with pytest.raises(ValueError):
            counter.update(invalid)
    with pytest.raises(ValueError):
        Morris8(rng, 16)
    assert morris_metrics(0, 0)["error_relativo_porcentaje"] == 0
    assert morris_metrics(100, 75) == {"exacto_csv": 100, "estimacion_morris": 75,
                                      "diferencia_con_signo": -25, "error_absoluto": 25,
                                      "error_relativo_porcentaje": 25}


def test_simulator_rng_unaffected_by_morris():
    plain = list(generate_events())
    interleaved = []
    morris = GatewayMorris()
    for event in generate_events():
        morris.update(event.pasarela, event.fallos)
        interleaved.append(event)
    assert plain == interleaved
    assert morris.counters["Ámbar"].rng is not morris.counters["Cobalto"].rng


def test_writer_incremental_order_reset_and_closed(tmp_path):
    events = list(generate_events())[:4]
    with CSVEventWriter(tmp_path) as writer:
        writer.write(events[0])
        writer.flush()
        assert len(pd.read_csv(tmp_path/"ambar.csv")) == 1
        assert len(pd.read_csv(tmp_path/"cobalto.csv")) == 0
        with pytest.raises(ValueError, match="duplicada"):
            writer.write(events[0])
        with pytest.raises(ValueError, match="paridad"):
            writer.write(replace(events[1], pasarela="Ámbar"))
        writer.write(events[1])
    with pytest.raises(RuntimeError):
        writer.write(events[2])
    with CSVEventWriter(tmp_path) as writer:
        assert len(pd.read_csv(tmp_path/"ambar.csv")) == 0


@pytest.mark.parametrize("field,value", [("id", 1.5), ("perfil", "desconocido"), ("fallos", 999),
                                         ("cuentas", None), ("instante", "2026-11-10T08:01"), ("pasarela", "Cobalto")])
def test_raw_rejects_malformed_data(real_run, tmp_path, field, value):
    exp, _ = real_run
    for file in exp.paths.data.glob("*.csv"):
        (tmp_path/file.name).write_bytes(file.read_bytes())
    frame = pd.read_csv(tmp_path/"ambar.csv")
    frame[field] = frame[field].astype(object)
    frame.loc[0, field] = value
    frame.to_csv(tmp_path/"ambar.csv", index=False)
    with pytest.raises(ValueError):
        validate_raw(tmp_path)


def test_projection_cannot_be_detached_from_source(real_run):
    exp, _ = real_run
    projected = exp.snapshot()
    projected.loc[0, "fallos"] += 1
    with pytest.raises(ValueError, match="corresponde"):
        validate_projection(projected, exp.from_csv())
