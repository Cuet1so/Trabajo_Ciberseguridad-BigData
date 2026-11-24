"""Audita una ejecución sin modificarla; --require-ml valida también modelos reales."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analytics import FixedUMAPClusters
from config import FEATURE_COLUMNS, GATEWAYS
from morris import GatewayMorris
from storage import RunPaths, check_manifest
from validation import require, validate_projection, validate_raw


def validate(output_dir: Path, *, require_ml: bool = False) -> dict[str, object]:
    paths = RunPaths(Path(output_dir))
    manifest = check_manifest(paths)
    data = validate_raw(paths.data)
    replay = GatewayMorris()
    for gateway, failures in zip(data.pasarela, data.fallos, strict=True):
        replay.update(str(gateway), int(failures))
    totals = data.groupby("pasarela").fallos.sum().to_dict()
    estimates = {g: replay.estimate(g) for g in GATEWAYS}
    summary = json.loads((paths.results / "resumen_defensa.json").read_text(encoding="utf-8"))
    for gateway in GATEWAYS:
        require(summary["morris"][gateway]["exacto_csv"] == totals[gateway], "Total exacto incoherente")
        require(summary["morris"][gateway]["estimacion_morris"] == estimates[gateway], "Morris incoherente")
        require(summary["morris"][gateway]["registros_finales"] == replay.counters[gateway].registers, "Registros Morris incoherentes")
    projected_file = paths.results / "eventos_proyectados.csv"
    available = projected_file.exists()
    if available:
        validate_projection(pd.read_csv(projected_file), data)
    if require_ml:
        require(manifest["ml_real"], "Se requieren UMAP y K-means reales, no una ejecución diagnóstica")
        from review import ReviewedRun
        review = ReviewedRun(output_dir)
        models = FixedUMAPClusters.load(output_dir, trusted_local=True)
        features = data.loc[:299, list(FEATURE_COLUMNS)].to_numpy(dtype=float)
        require(models.scaler.n_samples_seen_ == 300, "Scaler ajustado con otro número de eventos")
        require(np.allclose(models.scaler.mean_, features.mean(axis=0)), "Scaler no corresponde a los 300 iniciales")
        require(np.allclose(models.scaler.var_, features.var(axis=0)), "Varianza del scaler incorrecta")
        require(np.allclose(models.reducer._raw_data, models.scaler.transform(features)), "UMAP no conserva los 300 vectores iniciales")
        require(np.allclose(models.reducer.embedding_, review.snapshot().iloc[:300][["umap_x", "umap_y"]]), "Proyección inicial distinta del modelo")
        require(np.array_equal(models.kmeans.predict(review.snapshot()[["umap_x", "umap_y"]].to_numpy()), review.snapshot().cluster), "K-means persistido incoherente")
        require(models.kmeans.n_clusters == 3, "K-means debe tener tres grupos")
    return {"eventos": len(data), "minutos": len(data)//2, "exactos": totals, "morris": estimates,
            "proyeccion_disponible": available, "ml_real": manifest["ml_real"], "integridad": "correcta"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Raíz con datos/, resultados/ y modelos/")
    parser.add_argument("--require-ml", action="store_true", help="Carga exclusivamente los modelos locales de confianza de esta ejecución")
    args = parser.parse_args()
    print(json.dumps(validate(args.output_dir, require_ml=args.require_ml), indent=2, ensure_ascii=False))
    print("VERIFICACIÓN COMPLETADA")


if __name__ == "__main__":
    main()
