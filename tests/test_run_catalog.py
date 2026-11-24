import json
from pathlib import Path

from run_catalog import completed_runs


def test_catalog_skips_partial_locked_diagnostic_and_invalid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name, manifest in {
        'finished': {'estado': 'completa', 'ml_real': True},
        'partial': {'estado': 'parcial', 'ml_real': True},
        'diagnostic': {'estado': 'completa', 'ml_real': False},
        'locked': {'estado': 'completa', 'ml_real': True},
        'invalid': [],
    }.items():
        root = Path('ejecuciones') / name
        root.mkdir(parents=True)
        (root / 'ejecucion.json').write_text(json.dumps(manifest))
    Path('ejecuciones/locked/.execution.lock').touch()
    assert completed_runs() == ['ejecuciones/finished']
