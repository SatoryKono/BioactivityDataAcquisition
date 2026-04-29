"""Shared context object for composite bootstrap infrastructure primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bioetl.domain.ports import (
    ClockPort,
    LockPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.infrastructure.config import Settings


@dataclass(frozen=True, slots=True)
class CompositeInfrastructureContext:
    """Bundle of infrastructure primitives required by composite bootstrap."""

    run_id: str
    settings: Settings
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    storage: (
        Any  # Any: concrete storage adapter implements the narrow storage ports
    )
    lock: LockPort
    clock: ClockPort | None = None
