"""Shared context object for composite bootstrap infrastructure primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bioetl.domain.ports import LockPort, LoggerPort, MetricsPort, TracingPort
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
        Any  # Any: storage adapter is concrete infra object implementing StoragePort
    )
    lock: LockPort
