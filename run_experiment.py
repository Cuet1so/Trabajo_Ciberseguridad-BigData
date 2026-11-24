"""Ejecución completa real con el mismo motor y finalización que Streamlit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline import StreamingExperiment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Raíz de ejecución; conserva la anterior en historial/")
    parser.add_argument("--sin-ml", action="store_true", help="Diagnóstico incompleto; no habilita modo revisión")
    args = parser.parse_args()
    with StreamingExperiment(output_dir=args.output_dir, use_ml=not args.sin_ml) as exp:
        while not exp.is_finished:
            exp.step()
            if exp.event_count % 500 == 0 or exp.event_count == 300:
                print(f"Procesados: {exp.event_count}/6000", flush=True)
        summary = json.loads((exp.paths.results / "resumen_defensa.json").read_text(encoding="utf-8"))
        for gateway, values in summary["morris"].items():
            print(f"{gateway}: exacto={values['exacto_csv']}, Morris={values['estimacion_morris']:.2f}, "
                  f"error={values['error_relativo_porcentaje']:.2f}%")
        print(summary["interpretacion"])
        print(f"Informe: {exp.paths.results / 'Informe_Defensa_Tecnica.pdf'}")
        if not args.sin_ml:
            print(f"Revisión: python -m streamlit run app.py -- --review {args.output_dir}")
        else:
            print("Diagnóstico sin ML: la ejecución no admite revisión visual ni satisface la rúbrica completa.")


if __name__ == "__main__":
    main()
