"""Detector exploratorio causal; nunca consulta el punto de cambio ni el perfil."""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

import numpy as np

from config import GATEWAYS
from simulator import SecurityEvent


@dataclass(frozen=True, slots=True)
class DetectionConfig:
    window: int = 100
    baseline_events: int = 300  # Por pasarela, referencia fijada al observarlos.
    stride: int = 20
    persistence: int = 3
    min_increase: float = 3.0  # Cuentas/min sobre referencia Cobalto.
    relative_increase: float = 0.5
    min_control_gap: float = 3.0  # Aumento Cobalto menos aumento Ámbar.

    def __post_init__(self) -> None:
        if self.window != 100 or self.baseline_events < self.window:
            raise ValueError("Ventana obligatoria de 100; referencia de al menos 100 resúmenes")
        if self.stride < 1 or self.persistence < 1:
            raise ValueError("Paso y persistencia deben ser positivos")
        for value in (self.min_increase, self.relative_increase, self.min_control_gap):
            if not isfinite(value) or value <= 0:
                raise ValueError("Los umbrales deben ser finitos y positivos")


class ChangeDetector:
    def __init__(self, config: DetectionConfig = DetectionConfig()):
        self.config = config
        self.windows: dict[str, deque[tuple[int, int]]] = {
            g: deque(maxlen=config.window) for g in GATEWAYS
        }
        self.counts = dict.fromkeys(GATEWAYS, 0)
        self.baseline_sums = dict.fromkeys(GATEWAYS, 0.0)
        self.baseline: dict[str, float] = {}
        self.history: list[dict[str, Any]] = []
        self.first_detection: dict[str, Any] | None = None
        self.streak = 0
        self._last_id = 0

    def update(self, event: SecurityEvent) -> None:
        if event.id != self._last_id + 1:
            raise ValueError("El detector necesita eventos consecutivos, sin duplicados")
        self._last_id = event.id
        gateway = event.pasarela
        self.counts[gateway] += 1
        count = self.counts[gateway]
        self.windows[gateway].append((event.cuentas, event.fallos))
        if count <= self.config.baseline_events:
            self.baseline_sums[gateway] += event.cuentas
            if count == self.config.baseline_events:
                self.baseline[gateway] = self.baseline_sums[gateway] / count
        # Cobalto cierra la pareja: ninguna comparación usa el minuto siguiente.
        if gateway != "Cobalto" or min(self.counts.values()) < self.config.window:
            return
        means = {g: np.mean(self.windows[g], axis=0) for g in GATEWAYS}
        row: dict[str, Any] = {
            "id": event.id, "instante": event.instante, "minuto": count,
            **{f"cuentas_{g}": float(means[g][0]) for g in GATEWAYS},
            **{f"fallos_{g}": float(means[g][1]) for g in GATEWAYS},
            "evaluable": False, "candidato": False, "persistencia": self.streak,
            "cambio_observado": self.first_detection is not None,
        }
        if len(self.baseline) == 2:
            increase = float(means["Cobalto"][0]) - self.baseline["Cobalto"]
            control = float(means["Ámbar"][0]) - self.baseline["Ámbar"]
            threshold = max(self.config.min_increase,
                            self.config.relative_increase * self.baseline["Cobalto"])
            row.update(aumento_cobalto=increase, diferencia_control=increase-control,
                       umbral=threshold, referencia_cobalto=self.baseline["Cobalto"],
                       referencia_ambar=self.baseline["Ámbar"])
            # La primera ventana evaluada empieza DESPUÉS de la referencia.
            first = self.config.baseline_events + self.config.window
            if count >= first and (count-first) % self.config.stride == 0:
                candidate = increase >= threshold and increase-control >= self.config.min_control_gap
                self.streak = self.streak + 1 if candidate else 0
                row.update(evaluable=True, candidato=candidate, persistencia=self.streak)
                if self.streak >= self.config.persistence and self.first_detection is None:
                    row["cambio_observado"] = True
                    self.first_detection = row.copy()
        self.history.append(row)

    def summary(self) -> dict[str, Any]:
        return {"configuracion": asdict(self.config), "referencia": self.baseline.copy(),
                "primera_deteccion": self.first_detection}
