"""Simulación en orden cronológico y escritura incremental por pasarela."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, TextIO

import numpy as np

from config import (
    CONFIG, CSV_COLUMNS, DISTRIBUTIONS, FEATURE_COLUMNS, GATEWAY_FILES,
    GATEWAYS, PROFILE_RANGES, PROFILES, ExperimentConfig,
)


@dataclass(frozen=True, slots=True)
class SecurityEvent:
    id: int
    instante: str
    pasarela: str
    accesos_correctos: int
    fallos: int
    cuentas: int
    ips_origen: int
    perfil: str

    def as_row(self) -> dict[str, object]:
        return asdict(self)

    def features(self) -> list[float]:
        return [float(getattr(self, name)) for name in FEATURE_COLUMNS]


def generate_events(config: ExperimentConfig = CONFIG) -> Iterator[SecurityEvent]:
    """Produce exactamente 6000 eventos: impar Ámbar, par Cobalto.

    La única fuente de aleatoriedad de perfiles y medidas es la semilla 42.
    Las dos pasarelas comparten instante para cada pareja sucesiva.
    """
    rng = np.random.default_rng(config.simulator_seed)
    for event_id in range(1, config.total_events + 1):
        gateway = GATEWAYS[(event_id + 1) % 2]  # 1->Ámbar, 2->Cobalto
        minute = (event_id - 1) // 2
        timestamp = (config.start_at + timedelta(minutes=minute)).isoformat(timespec="minutes")
        distribution = (
            DISTRIBUTIONS["cobalto_despues"]
            if event_id > config.change_event and gateway == "Cobalto"
            else DISTRIBUTIONS["normal"]
        )
        profile = str(rng.choice(PROFILES, p=distribution))
        measures = [int(rng.integers(lo, hi + 1)) for lo, hi in PROFILE_RANGES[profile]]
        yield SecurityEvent(event_id, timestamp, gateway, *measures, profile)


class CSVEventWriter:
    """Un archivo por pasarela, creado vacío al iniciar cada ejecución."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._files: dict[str, TextIO] = {}
        self._writers: dict[str, csv.DictWriter] = {}
        self._closed = False
        self._last_id = 0
        for gateway, basename in GATEWAY_FILES.items():
            handle = (self.output_dir / basename).open("w", encoding="utf-8", newline="")
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            self._files[gateway] = handle
            self._writers[gateway] = writer
        self.flush()

    def write(self, event: SecurityEvent) -> None:
        if self._closed:
            raise RuntimeError("No se pueden escribir eventos en archivos cerrados.")
        if event.id != self._last_id + 1:
            raise ValueError("Escritura fuera de orden o duplicada")
        if event.pasarela != GATEWAYS[(event.id + 1) % 2]:
            raise ValueError("La pasarela no corresponde a la paridad del ID")
        self._writers[event.pasarela].writerow(event.as_row())
        self._last_id = event.id

    def flush(self) -> None:
        if self._closed:
            return
        for handle in self._files.values():
            handle.flush()

    def close(self) -> None:
        if not self._closed:
            self.flush()
            for handle in self._files.values():
                handle.close()
            self._closed = True

    def __enter__(self) -> "CSVEventWriter":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
