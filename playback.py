"""Reloj de reproducción independiente del generador y de los reruns de widgets."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Protocol


class IncrementalRun(Protocol):
    is_finished: bool
    def step(self) -> int: ...


@dataclass
class PlaybackClock:
    interval: float = .6
    playing: bool = False
    next_due: float = 0.0

    def set_interval(self, seconds: float, now: float) -> None:
        if not isfinite(seconds) or seconds < .1:
            raise ValueError("El intervalo mínimo es 0,1 segundos")
        self.interval = seconds
        self.next_due = now + seconds

    def resume(self, now: float, *, immediate: bool = False) -> None:
        self.playing = True
        self.next_due = now if immediate else now + self.interval

    def pause(self) -> None:
        self.playing = False

    def tick(self, exp: IncrementalRun, now: float) -> int:
        if exp.is_finished:
            self.pause()
        if not self.playing or now < self.next_due:
            return 0
        # Un rerun no puede procesar de nuevo el mismo vencimiento.
        self.next_due = now + self.interval
        processed = exp.step()
        if exp.is_finished:
            self.pause()
        return processed
