"""Checkpoint and recovery service for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchCheckpointRecoveryService"]

import time
from typing import TYPE_CHECKING, cast

from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointRuntimeService,
    )
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort


class BatchCheckpointRecoveryService:
    """Owns checkpoint save semantics for runtime, shutdown, and recovery."""

    _CHECKPOINT_TRACER_NAME = "bioetl.checkpoint"

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

    async def save_periodic_checkpoint(
        self,
        *,
        records_fetched: int,
        resume_offset: int,
        checkpoint_interval: int,
    ) -> None:
        """Save a periodic checkpoint when the interval threshold is reached."""
        # Guard before modulo: zero would fail or never match a useful threshold.
        if checkpoint_interval <= 0 or records_fetched <= 0:
            return
        if records_fetched % checkpoint_interval != 0:
            return
        total = self._total_processed(records_fetched, resume_offset)
        await self._save_checkpoint(total, operation="periodic")

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
                self._emit_checkpoint_save_event(
                    operation="exception",
                    status="skipped",
                )
                return
            await self._save_checkpoint(total, operation="exception")
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
            await self._save_checkpoint(total, operation="shutdown")
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
        await self._save_checkpoint(total, operation="manual")

    @staticmethod
    def _total_processed(records_fetched: int, resume_offset: int) -> int:
        return resume_offset + records_fetched

    def _emit_checkpoint_save_event(self, *, operation: str, status: str) -> None:
        if self._metrics is None:
            return
        self._metrics.increment_counter(
            "bioetl_checkpoint_save_events_total",
            1,
            {
                "pipeline": self._pipeline_name,
                "operation": operation,
                "status": status,
            },
        )

    def _observe_checkpoint_save_duration(
        self,
        *,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        if self._metrics is None:
            return
        self._metrics.observe_histogram(
            "bioetl_checkpoint_save_duration_seconds",
            duration_seconds,
            {
                "pipeline": self._pipeline_name,
                "operation": operation,
                "status": status,
            },
        )

    def _start_checkpoint_save_span(
        self,
        *,
        operation: str,
        records_processed: int,
    ) -> Span | None:
        if self._tracer is None:
            return None
        span = cast(
            "Span",
            cast(
                object,
                self._tracer.get_tracer(
                    self._CHECKPOINT_TRACER_NAME
                ).start_as_current_span(
                    "checkpoint_save",
                    attributes={
                        "bioetl.pipeline": self._pipeline_name,
                        "bioetl.checkpoint.operation": operation,
                        "bioetl.checkpoint.scope": "ordinary",
                        "bioetl.checkpoint.records_processed": records_processed,
                    },
                ),
            ),
        )
        span.__enter__()
        return span

    def _close_checkpoint_save_span(
        self,
        span: Span | None,
        *,
        status: str,
        error: BaseException | None = None,
    ) -> None:
        if span is None:
            return
        span.set_attribute("bioetl.checkpoint.status", status)
        if error is not None:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(error).__name__)
            if isinstance(error, Exception):
                span.record_exception(error)
        span.__exit__(None, None, None)
        # Lifecycle/end-of-run paths own flush; per-checkpoint flush can block.

    async def _save_checkpoint(self, total: int, *, operation: str) -> None:
        started_at = time.monotonic()
        span = self._start_checkpoint_save_span(
            operation=operation,
            records_processed=total,
        )
        try:
            await self._checkpoint_manager.save_checkpoint(
                self._checkpoint_payload(total)
            )
        except self._checkpoint_save_errors as error:
            duration_seconds = time.monotonic() - started_at
            self._emit_checkpoint_save_event(
                operation=operation,
                status="failed",
            )
            self._observe_checkpoint_save_duration(
                operation=operation,
                status="failed",
                duration_seconds=duration_seconds,
            )
            self._close_checkpoint_save_span(
                span,
                status="failed",
                error=error,
            )
            raise
        duration_seconds = time.monotonic() - started_at
        self._emit_checkpoint_save_event(
            operation=operation,
            status="succeeded",
        )
        self._observe_checkpoint_save_duration(
            operation=operation,
            status="succeeded",
            duration_seconds=duration_seconds,
        )
        self._close_checkpoint_save_span(
            span,
            status="succeeded",
        )

    def _checkpoint_payload(self, total: int) -> CheckpointMetadata | int:
        """Build checkpoint payload, including memory trace when available."""
        if self._memory_manager is None:
            return total
        memory_trace = self._memory_manager.decision_trace_dicts()
        if not memory_trace:
            return total
        return CheckpointMetadata(
            records_processed=total,
            memory_decision_trace=memory_trace,
        )
