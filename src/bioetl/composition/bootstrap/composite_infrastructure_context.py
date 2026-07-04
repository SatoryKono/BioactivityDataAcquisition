"""Shared context object for composite bootstrap infrastructure primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.domain.ports import (
    ClockPort,
    LockPort,
    LoggerPort,
    MergedStoragePort,
    MetricsPort,
    SilverStoragePort,
    TracingPort,
)
from bioetl.infrastructure.config.settings_api import Settings


class CompositeRuntimeStorageProtocol(MergedStoragePort, SilverStoragePort, Protocol):
    """Storage capabilities required by composite runtime bootstrap."""


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
