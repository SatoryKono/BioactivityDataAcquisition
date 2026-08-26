"""Metrics factory/service ports migrated from composition (ADR-058)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort

    Settings = object


@runtime_checkable
class WorkflowMetricsFactoryProtocol(Protocol):
    """Lazy metrics-factory contract for canonical workflow settings."""

    def __call__(self, settings: Settings, /) -> MetricsPort: ...


@runtime_checkable
class MetricsFactoryProtocol(Protocol):
    """Factory-like contract for constructing a metrics port from settings."""

    def _create_metrics(self, settings: Settings) -> MetricsPort: ...


@runtime_checkable
class MetricsStartResult(Protocol):
    """Result of starting the metrics HTTP server."""

    success: bool
    error: str | None
    port: int


@runtime_checkable
class MetricsServerStatus(Protocol):
    """Runtime status of the metrics HTTP server."""

    running: bool
    port: int | None
    started_at: datetime | None


@runtime_checkable
class MetricsGatewayResult(Protocol):
    """Result of a Pushgateway publish or delete."""

    success: bool
    error: str | None


@runtime_checkable
class MetricsService(Protocol):
    """Metrics HTTP server lifecycle contract used by composition bootstrap."""

    logger: LoggerPort | object

    def start(
        self,
        port: int,
        addr: str,
        *,
        fail_fast: bool,
        retry_count: int,
        retry_delay: float,
    ) -> MetricsStartResult: ...

    def get_status(self) -> MetricsServerStatus: ...

    def push_to_gateway(
        self,
        *,
        gateway: str,
        run_label: str = "bioetl",
        grouping_key: dict[str, str] | None = None,
        metric_names: tuple[str, ...] | None = None,
    ) -> MetricsGatewayResult: ...

    def delete_from_gateway(
        self,
        *,
        gateway: str,
        run_label: str,
        grouping_key: dict[str, str],
    ) -> MetricsGatewayResult: ...
