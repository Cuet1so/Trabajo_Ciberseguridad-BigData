"""Catálogo local de ejecuciones; la selección se verifica íntegramente al cargar."""
from __future__ import annotations

import json
from pathlib import Path


def completed_runs(root: Path = Path("ejecuciones")) -> list[str]:
    """Lista manifiestos completos sin cargar modelos ni leer todos los CSV.

    Este catálogo no valida la integridad: ReviewedRun comprueba la ejecución elegida.
    """
    candidates = [Path("."), *sorted(root.glob("*"), reverse=True)]
    available = []
    for path in candidates:
        if (path / ".execution.lock").exists():
            continue
        try:
            manifest = json.loads((path / "ejecucion.json").read_text(encoding="utf-8"))
            if manifest.get("estado") == "completa" and manifest.get("ml_real"):
                available.append(str(path))
        except (OSError, ValueError, AttributeError):
            continue
    return available
