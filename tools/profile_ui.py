"""Mide construcción de figuras y lectura CSV de la vista inicial de revisión."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path.cwd()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    args = parser.parse_args()
    from review import ReviewedRun
    from streamlit.testing.v1 import AppTest
    import bi_charts
    import pandas as pd
    records: dict[str, list[float]] = {}
    for name in ("morris_evolution", "morris_error", "umap_map", "profile_heatmap", "group_distribution", "before_after"):
        original = getattr(bi_charts, name)

        def timed(*args, _fn=original, _name=name, **kwargs):
            start = perf_counter()
            result = _fn(*args, **kwargs)
            records.setdefault(_name, []).append(perf_counter() - start)
            return result

        setattr(bi_charts, name, timed)
    start = perf_counter()
    run = ReviewedRun(Path("."))
    review_time = perf_counter() - start
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=60)
    app.session_state["reviewed"] = run
    app.session_state["mode"] = "Revisión"
    app.session_state["navigation"] = "Simulación"
    app.run()
    assert not app.exception
    readings = []
    for _ in range(10):
        start = perf_counter()
        pd.concat([pd.read_csv(run.paths.data / name) for name in ("ambar.csv", "cobalto.csv")])
        readings.append(perf_counter() - start)
    result = dict(revision_validacion_s=review_time, construccion_graficos_s=records, lecturas_csv_6000_s=readings)
    output = Path("docs/auditoria_final")
    output.mkdir(parents=True, exist_ok=True)
    (output / f"perfil_{args.label}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
