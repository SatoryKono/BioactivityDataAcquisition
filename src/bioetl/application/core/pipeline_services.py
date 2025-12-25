"""Pipeline services - injected dependencies.

Part of BasePipeline decomposition (ADR-0005).
Separates I/O port dependencies from pipeline logic.

Logger and Metrics are formalized as ports (ADR-005).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Self

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

    def __post_init__(self) -> None:
        """Validate that all services are provided."""
        # Validation is implicit - dataclass requires all non-default fields
        # Runtime checks happen via Protocol structural typing
        pass

    async def __aenter__(self) -> Self:
        """Enter the async context manager, initializing services."""
        await self.data_source.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager, closing services."""
        await self.aclose()

    async def aclose(self) -> None:
        """Gracefully close all I/O resources and observability."""
        self.logger.info("Closing pipeline services...")

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
                self.logger.error("Error during service shutdown", error=result)

        # Close observability (sync, best-effort)
        self._close_observability()

        self.logger.info("Pipeline services closed.")

    def _close_observability(self) -> None:
        """Close metrics and tracing resources (sync, idempotent)."""
        try:
            self.metrics.close()
        except Exception as e:
            self.logger.warning("Error closing metrics", error=str(e))

        try:
            self.tracing.close()
        except Exception as e:
            self.logger.warning("Error closing tracing", error=str(e))


__all__ = ["PipelineServices"]
