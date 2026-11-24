from collections import Counter

import pandas as pd

from config import CONFIG, PROFILE_RANGES
from simulator import generate_events


def test_all_6000_ids_gateways_and_minute_pairs():
    rows = list(generate_events())
    assert len(rows) == 6000
    assert [r.id for r in rows] == list(range(1, 6001))
    assert sum(r.pasarela == "Ámbar" for r in rows) == 3000
    assert sum(r.pasarela == "Cobalto" for r in rows) == 3000
    assert all(rows[i].instante == rows[i + 1].instante for i in range(0, len(rows), 2))
    assert all(rows[i].pasarela == "Ámbar" and rows[i+1].pasarela == "Cobalto" for i in range(0,len(rows),2))
    assert rows[0].instante == "2026-11-10T08:00"


def test_each_measure_in_inclusive_profile_range():
    for e in generate_events():
        for name,(lo,hi) in zip(("accesos_correctos","fallos","cuentas","ips_origen"),PROFILE_RANGES[e.perfil], strict=True):
            assert lo <= getattr(e,name) <= hi


def test_rng_is_deterministic_and_change_applies_to_cobalto_only():
    a = list(generate_events())
    b = list(generate_events())
    assert a == b
    normal_before = [e for e in a if e.id <= 3000 and e.pasarela == "Cobalto"]
    changed_after = [e for e in a if e.id > 3000 and e.pasarela == "Cobalto"]
    assert sum(e.perfil == "fallos_repartidos" for e in changed_after) > 800
    assert sum(e.perfil == "fallos_repartidos" for e in normal_before) < 300
