"""Agregaciones de presentación independientes de Streamlit y de los modelos ML.

Los promedios representan resúmenes por minuto, nunca cuentas únicas globales.
"""
from __future__ import annotations

import pandas as pd

from config import GATEWAYS


def evolution_by_gateway(events: pd.DataFrame, minutes_per_bin: int = 100) -> pd.DataFrame:
    """Media observada por ventanas NO solapadas, sin utilizar minutos futuros.

    Cada par (Ámbar impar, Cobalto par) comparte el mismo minuto simulado.
    """
    if minutes_per_bin < 1:
        raise ValueError("La ventana debe ser un entero positivo")
    required = {"id", "pasarela", "fallos", "cuentas", "ips_origen"}
    if not required.issubset(events.columns):
        raise ValueError(f"Faltan columnas: {sorted(required - set(events.columns))}")
    if events.empty:
        return pd.DataFrame(columns=["pasarela", "bloque", "minuto_fin", "resumenes",
                                     "fallos_medios", "cuentas_medias", "ips_medias"])
    frame = events.loc[:, list(required)].copy()
    frame["minuto"] = (frame["id"].astype(int) + 1) // 2
    frame["bloque"] = (frame["minuto"] - 1) // minutes_per_bin
    result = (frame.groupby(["pasarela", "bloque"], observed=True)
              .agg(resumenes=("id", "count"),
                   ultimo_minuto=("minuto", "max"),
                   fallos_medios=("fallos", "mean"),
                   cuentas_medias=("cuentas", "mean"),
                   ips_medias=("ips_origen", "mean"))
              .reset_index())
    result = result.rename(columns={"ultimo_minuto": "minuto_fin"})
    return result.sort_values(["pasarela", "minuto_fin"]).reset_index(drop=True)


def gateway_kpis(events: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Indicadores acumulados calculados exclusivamente sobre eventos recibidos."""
    result: dict[str, dict[str, float]] = {}
    for gateway in GATEWAYS:
        subset = events.loc[events["pasarela"] == gateway]
        result[gateway] = {
            "resumenes": int(len(subset)),
            "fallos": int(subset["fallos"].sum()),
            "cuentas_medias": float(subset["cuentas"].mean()) if len(subset) else 0.0,
            "ips_medias": float(subset["ips_origen"].mean()) if len(subset) else 0.0,
        }
    return result
