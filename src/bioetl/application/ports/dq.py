"""DQ application ports migrated from composition (ADR-058)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.ports import DQMonitorPort

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


class DQDetectorConfig(Protocol):
    """Configuration surface used when wiring DQ thresholds."""

    min_baseline_samples: int

    def set_threshold(
        self,
        metric_name: str,
        *,
        min_value: float,
        max_value: float,
    ) -> None: ...


class ConfigurableDQMonitor(DQMonitorPort, Protocol):
    """DQ monitor contract with detector configuration support."""

    detector: DQDetectorConfig


class DQReportServiceFactoryProtocol(Protocol):
    """Callable contract for constructing a DQ report service."""

    def __call__(
        self,
        *,
        logger: LoggerPort,
        bronze_analyzer: object,
        silver_analyzer: object,
        gold_analyzer: object,
        report_writer: object,
        metrics: MetricsPort | None,
    ) -> object: ...


DQReportServiceFactory = DQReportServiceFactoryProtocol
