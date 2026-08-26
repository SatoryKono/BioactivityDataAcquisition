"""Metrics factory/service ports migrated from composition (ADR-058)."""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True, slots=True)
class MetricsStartResult:
    """Result of starting the metrics HTTP server."""

    success: bool = False
    port: int = 0
    addr: str = "127.0.0.1"
    already_running: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class MetricsServerStatus:
    """Runtime status of the metrics HTTP server."""

    running: bool = False
    port: int | None = None
    started_at: datetime | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class MetricsGatewayResult:
    """Result of a Pushgateway publish or delete."""

    success: bool = False
    gateway: str = ""
    run_label: str = ""
    grouping_key: dict[str, str] = field(default_factory=dict)
    error: str | None = None


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
