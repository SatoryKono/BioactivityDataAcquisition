"""Metrics factory/service ports migrated from composition (ADR-058)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

    Settings = object
    StartResult = object


@runtime_checkable
class WorkflowMetricsFactory(Protocol):
    """Lazy metrics-factory contract for canonical workflow settings."""

    def __call__(self, settings: Settings, /) -> MetricsPort: ...


class MetricsFactory(Protocol):
    def _create_metrics(self, settings: Settings) -> MetricsPort: ...


class MetricsService(Protocol):
    def start(
        self,
        port: int,
        addr: str,
        *,
        fail_fast: bool,
        retry_count: int,
        retry_delay: float,
    ) -> StartResult: ...
