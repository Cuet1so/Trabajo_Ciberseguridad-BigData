"""Rutas y persistencia local: datos, resultados y modelos separados."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import uuid4

PACKAGES = ("numpy", "pandas", "scipy", "scikit-learn", "umap-learn", "numba",
            "llvmlite", "pynndescent", "joblib", "streamlit", "plotly", "reportlab")


def versions() -> dict[str, str]:
    """Dependencias presentes, sin impedir un diagnóstico explícito sin UMAP/Streamlit."""
    installed = {"python": platform.python_version()}
    for name in PACKAGES:
        try:
            installed[name] = version(name)
        except PackageNotFoundError:
            installed[name] = "no_instalada"
    return installed


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


@dataclass(frozen=True)
class RunPaths:
    root: Path

    @property
    def data(self) -> Path:
        return self.root / "datos"

    @property
    def results(self) -> Path:
        return self.root / "resultados"

    @property
    def models(self) -> Path:
        return self.root / "modelos"

    @property
    def manifest(self) -> Path:
        return self.root / "ejecucion.json"


class RunLease:
    """Impide dos escritores en la misma raíz; conserva la ejecución anterior."""
    def __init__(self, paths: RunPaths):
        self.path = paths.root / ".execution.lock"
        paths.root.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open("x", encoding="utf-8") as handle:
                json.dump({"pid": os.getpid(), "host": platform.node()}, handle)
        except FileExistsError as exc:
            raise RuntimeError("Esta ejecución está ocupada (.execution.lock). Cierra el otro escritor; "
                               "si terminó abruptamente, comprueba que no siga activo antes de retirar el bloqueo.") from exc
        try:
            existing = [p for p in (paths.data, paths.results, paths.models, paths.manifest) if p.exists()]
            if existing:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
                archive = paths.root / "historial" / stamp
                archive.mkdir(parents=True)
                for path in existing:
                    shutil.move(str(path), archive / path.name)
            for directory in (paths.data, paths.results, paths.models):
                directory.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        self.path.unlink(missing_ok=True)


def seal_run(paths: RunPaths, metadata: dict[str, Any]) -> None:
    files = [p for folder in (paths.data, paths.results, paths.models) for p in folder.iterdir() if p.is_file()]
    write_json(paths.manifest, {**metadata, "schema": 1, "estado": "completa",
                              "sha256": {p.relative_to(paths.root).as_posix(): digest(p) for p in files}})


def check_manifest(paths: RunPaths) -> dict[str, Any]:
    if (paths.root / ".execution.lock").exists():
        raise ValueError("La ejecución tiene un escritor activo; no es revisable todavía")
    metadata = json.loads(paths.manifest.read_text(encoding="utf-8"))
    if metadata.get("schema") != 1 or metadata.get("estado") != "completa" or metadata.get("eventos") != 6000:
        raise ValueError("Manifiesto incompatible o ejecución incompleta")
    required = {"datos/ambar.csv", "datos/cobalto.csv", "resultados/resumen_defensa.json",
                "resultados/evolucion_morris.csv", "resultados/evolucion_cambios.csv",
                "resultados/Informe_Defensa_Tecnica.pdf", "resultados/DEFENSA_TECNICA.md"}
    if metadata.get("ml_real"):
        required |= {"resultados/eventos_proyectados.csv", "modelos/scaler.joblib",
                     "modelos/umap.joblib", "modelos/kmeans.joblib", "modelos/metadatos.json"}
    hashes = metadata.get("sha256", {})
    if not required.issubset(hashes):
        raise ValueError("El manifiesto no contiene todos los entregables obligatorios")
    for name, checksum in hashes.items():
        path = paths.root / name
        if path.is_symlink() or not path.resolve().is_relative_to(paths.root.resolve()):
            raise ValueError("El manifiesto contiene una ruta fuera de la ejecución local")
        if not path.is_file() or digest(path) != checksum:
            raise ValueError(f"Integridad incorrecta: {name}")
    return metadata
