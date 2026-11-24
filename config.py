"""Configuración reproducible del experimento (sin dependencias externas)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    total_events: int = 6_000
    initial_training_events: int = 300
    change_event: int = 3_000
    refresh_every: int = 100
    start_at: datetime = datetime(2026, 11, 10, 8, 0)
    simulator_seed: int = 42
    morris_seed: int = 420_042  # Flujo aleatorio independiente del simulador.
    umap_seed: int = 42
    kmeans_seed: int = 42
    registers_per_gateway: int = 8
    output_dir: Path = Path(".")  # Raíz de la ejecución: datos/, resultados/, modelos/.

    def __post_init__(self) -> None:
        required = (self.total_events, self.initial_training_events, self.change_event,
                    self.refresh_every, self.registers_per_gateway, self.simulator_seed)
        if required != (6000, 300, 3000, 100, 8, 42):
            raise ValueError("El experimento oficial exige 6000/300/3000/100 eventos, 8 registros y semilla 42")
        if (self.start_at.hour, self.start_at.minute, self.start_at.second, self.start_at.microsecond) != (8, 0, 0, 0):
            raise ValueError("La simulación debe empezar exactamente a las 08:00")


CONFIG = ExperimentConfig()
GATEWAYS = ("Ámbar", "Cobalto")
GATEWAY_FILES = {"Ámbar": "ambar.csv", "Cobalto": "cobalto.csv"}
PROFILES = ("pocos_fallos", "fallos_concentrados", "fallos_repartidos")
DISTRIBUTIONS = {
    "normal": (0.20, 0.70, 0.10),
    "cobalto_despues": (0.20, 0.10, 0.70),
}
# Intervalos inclusivos (accesos correctos, fallos, cuentas e IP de origen).
PROFILE_RANGES = {
    "pocos_fallos": ((40, 70), (2, 6), (1, 2), (1, 2)),
    "fallos_concentrados": ((40, 70), (30, 50), (1, 3), (1, 3)),
    "fallos_repartidos": ((40, 70), (30, 50), (20, 30), (8, 16)),
}
FEATURE_COLUMNS = ("accesos_correctos", "fallos", "cuentas", "ips_origen")
CSV_COLUMNS = ("id", "instante", "pasarela", *FEATURE_COLUMNS, "perfil")
