"""Contador aproximado de Morris: 8 réplicas por pasarela."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from config import CONFIG, GATEWAYS, ExperimentConfig


@dataclass(slots=True)
class Morris8:
    rng: np.random.Generator
    n_registers: int = 8
    registers: list[int] = field(init=False)

    def __post_init__(self) -> None:
        if self.n_registers != 8:
            raise ValueError("El enunciado exige exactamente ocho registros")
        self.registers = [0] * self.n_registers

    def update(self, failures: int) -> None:
        """Cada fallo representa 1 incremento lógico por registro.

        No es lo mismo contar un resumen que sus múltiples intentos fallidos.
        """
        if isinstance(failures, bool) or not isinstance(failures, (int, np.integer)) or failures < 0:
            raise ValueError("Los fallos deben ser un entero no negativo")
        for _ in range(failures):
            for i, c in enumerate(self.registers):
                if float(self.rng.random()) < 2.0 ** (-c):
                    self.registers[i] = c + 1

    @property
    def estimate(self) -> float:
        return sum((2 ** c - 1) for c in self.registers) / self.n_registers


class GatewayMorris:
    def __init__(self, config: ExperimentConfig = CONFIG):
        # Dos generadores independientes de la fuente de perfiles (semilla 42)
        # y distintos entre pasarelas; cada sorteo se utiliza una sola vez.
        seeds = np.random.SeedSequence(config.morris_seed).spawn(len(GATEWAYS))
        self.counters = {
            gateway: Morris8(np.random.default_rng(seed), config.registers_per_gateway)
            for gateway, seed in zip(GATEWAYS, seeds, strict=True)
        }

    def update(self, gateway: str, failures: int) -> None:
        self.counters[gateway].update(failures)

    def estimate(self, gateway: str) -> float:
        return self.counters[gateway].estimate
