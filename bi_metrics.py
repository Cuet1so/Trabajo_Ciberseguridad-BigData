"""Datos de presentación: reutiliza las estadísticas del informe, sin entrenar modelos."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import pandas as pd

from config import GATEWAYS
from report import cluster_characterization, comparison_table, metric_changes

BEFORE = "Antes (1–3000)"
AFTER = "Después (3001–6000)"
PERIOD_NAMES = {BEFORE: "Primera mitad", AFTER: "Segunda mitad"}
PROFILE_NAMES = {"pocos_fallos": "Pocos fallos", "fallos_concentrados": "Fallos concentrados", "fallos_repartidos": "Fallos repartidos"}


def number(value: float | int, decimals: int = 0, *, signed: bool = False) -> str:
    """Formato español solo para visualización; no redondea los datos originales."""
    if not isfinite(value):
        return "—"
    value = 0.0 if abs(value) < .5 * 10**(-decimals) else value
    text = format(value, f"{'+' if signed else ''},.{decimals}f")
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


@dataclass(frozen=True)
class MetricChange:
    before: float
    after: float
    difference: float
    percentage: float


@dataclass(frozen=True)
class DashboardData:
    raw: pd.DataFrame
    points: pd.DataFrame
    periods: pd.DataFrame
    changes: pd.DataFrame
    clusters: pd.DataFrame
    correspondence: pd.DataFrame

    @property
    def comparison_ready(self) -> bool:
        return len(self.periods) == 4 and bool(self.periods.minutos.eq(1500).all())

    def change(self, gateway: str, metric: str) -> MetricChange:
        if not self.comparison_ready:
            raise ValueError("La comparación final requiere 1500 resúmenes por pasarela y mitad")
        row = self.changes[(self.changes.pasarela == gateway) & (self.changes.metrica == metric)].iloc[0]
        return MetricChange(float(row.antes), float(row.despues), float(row.diferencia), float(row.variacion_porcentaje))

    @property
    def accounts_did(self) -> float:
        return self.change("Cobalto", "cuentas_medias").difference - self.change("Ámbar", "cuentas_medias").difference


def build_dashboard_data(raw: pd.DataFrame, points: pd.DataFrame) -> DashboardData:
    periods = comparison_table(points)
    clusters, correspondence = cluster_characterization(points)
    return DashboardData(raw, points, periods, metric_changes(periods), clusters, correspondence)


def filter_points(points: pd.DataFrame, gateway: str, period: str, groups: list[int]) -> pd.DataFrame:
    selected = points[points.cluster.isin(groups)]
    if gateway != "Ambas":
        selected = selected[selected.pasarela == gateway]
    if period != "Completo":
        selected = selected[selected.id.le(3000) if period == "Primera mitad" else selected.id.gt(3000)]
    return selected.copy()


# API de agregaciones presente en el repositorio remoto; se conserva su contrato.
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
