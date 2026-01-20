"""Pipeline services - injected dependencies.

Part of BasePipeline decomposition (ADR-0005).
Separates I/O port dependencies from pipeline logic.

Logger and Metrics are formalized as ports (ADR-005).
DQ report services added for optional DQ report generation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    DQMonitorPort,
    LockPort,
    LoggerPort,
    MetricsPort,
    QuarantinePort,
    StoragePort,
    TracingPort,
)

if TYPE_CHECKING:
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.ports import (
        BronzeDQAnalyzerPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        SilverDQAnalyzerPort,
    )


@dataclass(frozen=True)
class PipelineServices:
    """Injected dependencies for pipeline execution.

    All fields are Protocol-typed for testability and flexibility.
    This enables easy mocking in tests and swapping implementations.

    Frozen dataclass ensures services can't be accidentally replaced
    during pipeline execution.

    Attributes:
        data_source: Port for fetching data from external sources.
        storage: Port for writing to Bronze/Silver/Gold layers.
        lock: Port for distributed locking coordination.
        checkpoint: Port for pipeline state persistence.
        quarantine: Port for failed record isolation.
        metrics: Port for observability metrics collection.
        tracing: Port for distributed tracing.
        logger: Structured logger for pipeline events.
        dq_monitor: Optional data quality monitor for anomaly detection.
        bronze_dq_analyzer: Optional Bronze layer DQ analyzer for report generation.
        silver_dq_analyzer: Optional Silver layer DQ analyzer for report generation.
        gold_dq_analyzer: Optional Gold layer DQ analyzer for report generation.
        dq_report_writer: Optional DQ report writer for persisting reports.
        dq_report_service: Optional orchestration service for DQ reports.

    Example:
        >>> services = PipelineServices(
        ...     data_source=chembl_client,
        ...     storage=delta_storage,
        ...     lock=memory_lock,
        ...     checkpoint=local_checkpoint,
        ...     quarantine=unified_quarantine,
        ...     metrics=prometheus_metrics,
        ...     logger=logger,
        ... )

    """

    data_source: DataSourcePort
    storage: StoragePort
    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    metrics: MetricsPort
    tracing: TracingPort
    logger: LoggerPort
    dq_monitor: DQMonitorPort | None = None

    # DQ Report services (optional, created only if any layer has dq_report enabled)
    bronze_dq_analyzer: BronzeDQAnalyzerPort | None = None
    silver_dq_analyzer: SilverDQAnalyzerPort | None = None
    gold_dq_analyzer: GoldDQAnalyzerPort | None = None
    dq_report_writer: DQReportWriterPort | None = None
    dq_report_service: DQReportService | None = None

    def __post_init__(self) -> None:
        """Validate that all services are provided."""
        # Validation is implicit - dataclass requires all non-default fields
        # Runtime checks happen via Protocol structural typing

    async def __aenter__(self) -> Self:
        """Enter the async context manager, initializing services."""
        await self.data_source.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager, closing services."""
        await self.aclose()

    async def aclose(self) -> None:
        """Gracefully close all I/O resources and observability."""
        self.logger.info("Closing pipeline services...", stage="cleanup")

        # Close async I/O services
        results = await asyncio.gather(
            self.data_source.aclose(),
            self.storage.aclose(),
            self.lock.aclose(),
            self.checkpoint.aclose(),
            self.quarantine.aclose(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                self.logger.error(
                    "Error during service shutdown", stage="cleanup", error=result
                )

        # Close observability (sync, best-effort)
        self._close_observability()

        self.logger.info("Pipeline services closed.", stage="cleanup")

    def _close_observability(self) -> None:
        """Close metrics and tracing resources (sync, idempotent)."""
        try:
            self.metrics.close()
        except Exception as e:
            self.logger.warning("Error closing metrics", stage="cleanup", error=str(e))

        try:
            self.tracing.close()
        except Exception as e:
            self.logger.warning("Error closing tracing", stage="cleanup", error=str(e))


__all__ = ["PipelineServices"]
