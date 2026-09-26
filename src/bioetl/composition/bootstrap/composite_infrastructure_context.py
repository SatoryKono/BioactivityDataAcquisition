"""Shared context object for composite bootstrap infrastructure primitives."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.ports import (
    ClockPort,
    LockPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.infrastructure.config.settings_api import Settings

from bioetl.application.ports.storage import CompositeRuntimeStorageProtocol


@dataclass(frozen=True, slots=True)
class CompositeInfrastructureContext:
    """Bundle of infrastructure primitives required by composite bootstrap."""

    run_id: str
    settings: Settings
    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort
    storage: CompositeRuntimeStorageProtocol
    lock: LockPort
    clock: ClockPort | None = None


__all__ = ["CompositeInfrastructureContext", "CompositeRuntimeStorageProtocol"]
