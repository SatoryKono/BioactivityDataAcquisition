"""Checkpoint and recovery service for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchCheckpointRecoveryService"]

import time
from typing import TYPE_CHECKING

from bioetl.application.core.batch_checkpoint_save_observability import (
    close_checkpoint_save_span,
    emit_checkpoint_save_event,
    observe_checkpoint_save_duration,
    start_checkpoint_save_span,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

if TYPE_CHECKING:
    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointRuntimeService,
    )
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort


class BatchCheckpointRecoveryService:
    """Owns checkpoint save semantics for runtime, shutdown, and recovery."""

    def __init__(
        self,
        *,
        checkpoint_manager: CheckpointRuntimeService,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
        tracer: TracingPort | None = None,
        pipeline_name: str,
        memory_manager: BatchMemoryManagerService | None = None,
    ) -> None:
        self._checkpoint_manager = checkpoint_manager
        self._logger = logger
        self._metrics = metrics
        self._tracer = tracer
        self._pipeline_name = pipeline_name
        self._memory_manager = memory_manager
        self._checkpoint_save_errors = checkpoint_manager._operation_errors
        # Per-run progress watermark: highest ``records_fetched`` persisted
        # by ANY checkpoint operation in this run (they all persist the same
        # boundary). Periodic saves trigger when confirmed progress advanced
        # at least ``checkpoint_interval`` past it, regardless of batch-size
        # alignment. A failed save never advances it; a manual resume_offset
        # does not seed it (no durable boundary is proven for a manual offset).
        self._last_saved_progress: int = 0

    async def save_periodic_checkpoint(
        self,
        *,
        records_fetched: int,
        resume_offset: int,
        checkpoint_interval: int,
    ) -> None:
        """Save a periodic checkpoint when confirmed progress >= interval."""
        if checkpoint_interval <= 0 or records_fetched <= 0:
            return
        if records_fetched - self._last_saved_progress < checkpoint_interval:
            self._emit_event(operation="periodic", status="skipped")
            return
        total = self._total_processed(records_fetched, resume_offset)
        await self._save_checkpoint(
            total, operation="periodic", progress=records_fetched
        )

    async def save_checkpoint_on_exception(
        self,
        *,
        records_fetched: int,
        resume_offset: int,
        error: BaseException,
    ) -> None:
        """Persist a recovery checkpoint after a runtime exception."""
        try:
            total = self._total_processed(records_fetched, resume_offset)
            if total <= 0:
                self._emit_event(operation="exception", status="skipped")
                return
            await self._save_checkpoint(
                total, operation="exception", progress=records_fetched
            )
            self._logger.warning(
                "Checkpoint saved on exception for recovery",
                records_processed=total,
                error_type=type(error).__name__,
                reason="checkpoint_saved_on_pipeline_exception",
            )
        except self._checkpoint_save_errors as checkpoint_error:
            self._logger.warning(
                "Checkpoint save failed during exception handling",
                records_processed=self._total_processed(records_fetched, resume_offset),
                error_type=type(checkpoint_error).__name__,
                reason="checkpoint_save_failed_on_pipeline_exception",
            )

    async def save_checkpoint_on_shutdown(
        self,
        *,
        records_fetched: int,
        resume_offset: int,
    ) -> None:
        """Persist an emergency checkpoint during graceful shutdown."""
        try:
            total = self._total_processed(records_fetched, resume_offset)
            await self._save_checkpoint(
                total, operation="shutdown", progress=records_fetched
            )
        except self._checkpoint_save_errors as checkpoint_error:
            self._logger.warning(
                "Emergency checkpoint save failed during shutdown",
                records_processed=self._total_processed(records_fetched, resume_offset),
                error_type=type(checkpoint_error).__name__,
                reason="checkpoint_save_failed_on_shutdown",
            )

    async def save_checkpoint_now(
        self,
        *,
        records_fetched: int,
        resume_offset: int,
    ) -> None:
        """Persist a checkpoint immediately without recovery wrappers."""
        total = self._total_processed(records_fetched, resume_offset)
        await self._save_checkpoint(total, operation="manual", progress=records_fetched)

    @staticmethod
    def _total_processed(records_fetched: int, resume_offset: int) -> int:
        return resume_offset + records_fetched

    def _emit_event(self, *, operation: str, status: str) -> None:
        emit_checkpoint_save_event(
            self._metrics, self._pipeline_name, operation=operation, status=status
        )

    async def _save_checkpoint(
        self, total: int, *, operation: str, progress: int
    ) -> None:
        started_at = time.monotonic()
        span = start_checkpoint_save_span(
            self._tracer,
            self._pipeline_name,
            operation=operation,
            records_processed=total,
        )
        try:
            await self._checkpoint_manager.save_checkpoint(
                self._checkpoint_payload(total)
            )
            self._last_saved_progress = progress
        except self._checkpoint_save_errors as error:
            self._emit_event(operation=operation, status="failed")
            observe_checkpoint_save_duration(
                self._metrics,
                self._pipeline_name,
                operation=operation,
                status="failed",
                duration_seconds=time.monotonic() - started_at,
            )
            close_checkpoint_save_span(span, status="failed", error=error)
            raise
        self._emit_event(operation=operation, status="succeeded")
        observe_checkpoint_save_duration(
            self._metrics,
            self._pipeline_name,
            operation=operation,
            status="succeeded",
            duration_seconds=time.monotonic() - started_at,
        )
        close_checkpoint_save_span(span, status="succeeded")

    def _checkpoint_payload(self, total: int) -> CheckpointMetadata | int:
        from bioetl.application.core._checkpoint_payload import build_checkpoint_payload

        return build_checkpoint_payload(total, self._memory_manager)
