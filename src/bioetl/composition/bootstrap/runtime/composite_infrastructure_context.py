"""Context object for composite infrastructure primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bioetl.domain.ports import LockPort, LoggerPort, MetricsPort
from bioetl.infrastructure.config import Settings


@dataclass(frozen=True, slots=True)
class CompositeInfrastructureContext:
    """Bundle of infrastructure primitives required by composite runtime."""

    run_id: str
    settings: Settings
    logger: LoggerPort
    metrics: MetricsPort
    storage: (
        Any  # Any: storage adapter is concrete infra object implementing StoragePort
    )
    lock: LockPort
