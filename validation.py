"""Validación explícita de archivos; funciona también con python -O."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import CONFIG, CSV_COLUMNS, FEATURE_COLUMNS, GATEWAY_FILES, PROFILE_RANGES, PROFILES


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_raw(directory: Path) -> pd.DataFrame:
    frames = []
    for gateway, filename in GATEWAY_FILES.items():
        frame = pd.read_csv(directory / filename)
        require(list(frame.columns) == list(CSV_COLUMNS), f"Cabecera incorrecta: {filename}")
        require(len(frame) == 3000, f"Se requieren 3000 filas en {filename}")
        require(not frame.isna().any().any(), f"Datos ausentes en {filename}")
        for column in ("id", *FEATURE_COLUMNS):
            require(pd.api.types.is_integer_dtype(frame[column]), f"{column} debe ser entero: {filename}")
        require(frame.pasarela.eq(gateway).all(), f"Pasarela incorrecta: {filename}")
        start = 1 if gateway == "Ámbar" else 2
        require(np.array_equal(frame.id, np.arange(start, 6001, 2)), f"ID incorrectos o fuera de orden: {filename}")
        require(frame.perfil.isin(PROFILES).all(), "Perfil desconocido")
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True).sort_values("id").reset_index(drop=True)
    expected = np.repeat(pd.date_range(CONFIG.start_at, periods=3000, freq="min").strftime("%Y-%m-%dT%H:%M"), 2)
    require(np.array_equal(data.instante, expected), "Instantes incorrectos: se requieren parejas y minutos consecutivos")
    for profile, ranges in PROFILE_RANGES.items():
        group = data[data.perfil == profile]
        for feature, (lo, hi) in zip(FEATURE_COLUMNS, ranges, strict=True):
            require(group[feature].between(lo, hi).all(), f"Valor fuera del intervalo inclusivo: {profile}, {feature}")
    return data


def validate_projection(projected: pd.DataFrame, raw: pd.DataFrame) -> None:
    require(len(projected) == 6000, "La proyección requiere 6000 filas")
    require(set((*CSV_COLUMNS, "umap_x", "umap_y", "cluster")).issubset(projected.columns), "Faltan variables proyectadas")
    try:
        pd.testing.assert_frame_equal(projected[list(CSV_COLUMNS)], raw, check_dtype=False)
    except AssertionError as exc:
        raise ValueError("La proyección no corresponde exactamente a los CSV fuente") from exc
    require(np.isfinite(projected[["umap_x", "umap_y"]].to_numpy(dtype=float)).all(), "Coordenadas no finitas")
    require(pd.api.types.is_integer_dtype(projected.cluster) and projected.cluster.isin([0, 1, 2]).all(), "Etiquetas inválidas")


def compare_nested(actual: Any, expected: Any, path: str = "resumen") -> None:
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), f"Campos distintos: {path}")
        for key, value in expected.items():
            compare_nested(actual[key], value, f"{path}.{key}")
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), f"Longitud distinta: {path}")
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            compare_nested(a, e, f"{path}[{i}]")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        require(isinstance(actual, (int, float)) and np.isclose(actual, expected, rtol=1e-10, atol=1e-10), f"Valor incoherente: {path}")
    else:
        require(actual == expected, f"Valor incoherente: {path}")
