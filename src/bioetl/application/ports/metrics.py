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
class StartResult:
    """Result of starting the metrics server."""

    success: bool = False
    port: int = 0
    addr: str = "127.0.0.1"
    already_running: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class MetricsServerStatus:
    """Runtime status of the metrics server."""

    running: bool = False
    port: int | None = None
    started_at: datetime | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PushResult:
    """Result of publishing metrics to an external gateway."""

    success: bool = False
    gateway: str = ""
    run_label: str = ""
    grouping_key: dict[str, str] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteResult:
    """Result of deleting metrics from an external gateway."""

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
    ) -> StartResult: ...

    def get_status(self) -> MetricsServerStatus: ...

    def push_to_gateway(
        self,
        *,
        gateway: str,
        run_label: str = "bioetl",
        grouping_key: dict[str, str] | None = None,
        metric_names: tuple[str, ...] | None = None,
    ) -> PushResult: ...

    def delete_from_gateway(
        self,
        *,
        gateway: str,
        run_label: str,
        grouping_key: dict[str, str],
    ) -> DeleteResult: ...
