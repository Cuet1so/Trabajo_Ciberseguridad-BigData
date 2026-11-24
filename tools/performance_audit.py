"""Medición local comparable. Ejecutar desde la raíz: python tools/performance_audit.py etiqueta.

Dos ejecuciones secuenciales: primera en proceso y caliente en el mismo proceso.
No borra la caché Numba; no equivale a una máquina con instalación recién creada.
La latencia AppTest mide servidor, no pintura/transporte del navegador.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

sys.path.insert(0, str(Path.cwd()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/auditoria_final"))
    args = parser.parse_args()
    started = perf_counter()
    import numpy as np
    from pipeline import StreamingExperiment
    from streamlit.testing.v1 import AppTest
    imports = perf_counter() - started
    runs = []
    for phase in ("primera_en_proceso", "caliente_mismo_proceso"):
        with TemporaryDirectory(prefix="cyber_benchmark_") as directory:
            with StreamingExperiment(Path(directory)) as exp:
                fits = []
                original_fit = exp.projector.fit_initial

                def timed_fit(events):
                    start = perf_counter()
                    result = original_fit(events)
                    fits.append(perf_counter() - start)
                    return result

                exp.projector.fit_initial = timed_fit
                initial = perf_counter()
                exp.step()
                first = perf_counter() - initial
                batches = []
                while not exp.is_finished:
                    start = perf_counter()
                    exp.step()
                    batches.append(perf_counter() - start)
                total = perf_counter() - initial
                assert len(batches) == 57 and len(fits) == 1
                app = AppTest.from_file(Path("app.py").resolve(), default_timeout=60)
                app.session_state["experiment"] = exp
                start = perf_counter()
                app.run()
                render = perf_counter() - start
                assert not app.exception
                if "dashboard_view" in app.session_state:
                    app.session_state["dashboard_view"] = "Mapa UMAP y grupos"
                    app.run()
                timings = []
                for gateway in ("Cobalto", "Ámbar", "Ambas", "Cobalto", "Ambas"):
                    start = perf_counter()
                    app.selectbox(key="gateway_filter").set_value(gateway).run()
                    timings.append(perf_counter() - start)
                    assert not app.exception
                try:
                    import resource
                    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    rss *= 1 if sys.platform == "darwin" else 1024
                except ImportError:
                    rss = None
                runs.append(dict(fase=phase, primeros_300_s=first, ajuste_inicial_s=fits[0],
                                 lote_media_s=float(np.mean(batches)), lote_p95_s=float(np.percentile(batches, 95)),
                                 total_s=total, render_inicial_s=render,
                                 filtro_media_s=float(np.mean(timings)), filtro_p95_s=float(np.percentile(timings, 95)),
                                 max_rss_bytes=rss))
    result = dict(imports_s=imports, python=platform.python_version(), platform=platform.platform(), runs=runs)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / f"{args.label}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
