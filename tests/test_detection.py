from dataclasses import replace

import pytest

from config import GATEWAYS
from detection import ChangeDetector, DetectionConfig
from simulator import SecurityEvent, generate_events


def artificial_stream(minutes=800, shift_at=501):
    for minute in range(1, minutes+1):
        for offset, gateway in enumerate(GATEWAYS):
            accounts = 25 if gateway == "Cobalto" and minute >= shift_at else 2
            yield SecurityEvent(2*minute-1+offset, str(minute), gateway, 50, 40, accounts, 2, "unused")


def test_causal_reference_persistence_detects_shift_at_unannounced_time():
    detector = ChangeDetector()
    for event in artificial_stream():
        detector.update(event)
        if event.id <= 1000:
            assert detector.first_detection is None
    found = detector.first_detection
    assert found is not None
    assert 1000 < found["id"] < 1400  # Cambio independiente de 3001.
    assert found["persistencia"] == 3
    assert detector.baseline == {"Ámbar": 2, "Cobalto": 2}
    candidates = [row for row in detector.history if row["evaluable"] and row["id"] <= found["id"]]
    assert all(row["candidato"] for row in candidates[-3:])
    assert found["fallos_Cobalto"] == found["fallos_Ámbar"] == 40
    assert found["minuto"] >= 400


def test_future_profiles_do_not_affect_prior_results():
    events = list(generate_events())
    first, second = ChangeDetector(), ChangeDetector()
    for event in events[:3200]:
        first.update(event)
        second.update(replace(event, perfil="irrelevante"))
    assert first.history == second.history
    prefix = [row.copy() for row in first.history]
    for event in events[3200:]:
        first.update(event)
    assert first.history[:len(prefix)] == prefix


def test_stationary_control_and_short_spike_do_not_alert():
    detector = ChangeDetector()
    for event in artificial_stream(1000, 2000):
        if 1000 < event.id < 1020 and event.pasarela == "Cobalto":
            event = replace(event, cuentas=25)
        detector.update(event)
    assert detector.first_detection is None
    for kwargs in ({"window": 50}, {"persistence": 0}, {"min_increase": float("nan")}):
        with pytest.raises(ValueError):
            DetectionConfig(**kwargs)


def test_actual_detector_is_recorded_in_defense(real_run):
    exp, _ = real_run
    found = exp.detector.first_detection
    assert found is not None
    assert 3000 < found["id"] < 4000
