"""Metrics factory/service ports migrated from composition (ADR-058)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

    Settings = object
    StartResult = object


@runtime_checkable
class WorkflowMetricsFactoryProtocol(Protocol):
    """Lazy metrics-factory contract for canonical workflow settings."""

    def __call__(self, settings: Settings, /) -> MetricsPort: ...


class MetricsFactoryProtocol(Protocol):
    """Factory-like contract for constructing a metrics port from settings."""
    def _create_metrics(self, settings: Settings) -> MetricsPort: ...


class MetricsService(Protocol):
    """Metrics HTTP server lifecycle contract used by composition bootstrap."""
    def start(
        self,
        port: int,
        addr: str,
        *,
        fail_fast: bool,
        retry_count: int,
        retry_delay: float,
    ) -> StartResult: ...
