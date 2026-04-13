"""Checkpoint and recovery service for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchCheckpointRecoveryService"]


import time
from typing import TYPE_CHECKING

from bioetl.application.core.batch_runtime_failure_policy import OPERATION_ERRORS

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.domain.ports import LoggerPort, MetricsPort


class BatchCheckpointRecoveryService:
    """Owns checkpoint save semantics for runtime, shutdown, and recovery."""

    _CHECKPOINT_SAVE_ERRORS = OPERATION_ERRORS

    def __init__(
        self,
        *,
        checkpoint_manager: CheckpointManagerService,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
        pipeline_name: str,
    ) -> None:
        self._checkpoint_manager = checkpoint_manager
        self._logger = logger
        self._metrics = metrics
        self._pipeline_name = pipeline_name

    async def save_periodic_checkpoint(
        self,
        *,
        records_fetched: int,
        resume_offset: int,
        checkpoint_interval: int,
    ) -> None:
        """Save periodic checkpoint when interval threshold is reached.

        Args:
            records_fetched: Number of records fetched in the current run.
            resume_offset: Number of records already processed before resuming.
            checkpoint_interval: Frequency (in records) at which checkpoints are saved.
        """
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
        """Persist checkpoint on runtime exception for future resume.

        Args:
            records_fetched: Number of records fetched before the exception occurred.
            resume_offset: Number of records already processed before the current run.
            error: Exception that triggered checkpoint saving, used for log context.
        """
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
        except self._CHECKPOINT_SAVE_ERRORS as checkpoint_error:
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
        """Persist emergency checkpoint during graceful shutdown.

        Args:
            records_fetched: Number of records fetched before shutdown was requested.
            resume_offset: Number of records already processed before the current run.
        """
        try:
            total = self._total_processed(records_fetched, resume_offset)
            await self._save_checkpoint(total, operation="shutdown")
        except self._CHECKPOINT_SAVE_ERRORS as checkpoint_error:
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
        """Persist checkpoint immediately without internal recovery handling.

        Args:
            records_fetched: Number of records fetched in the current run.
            resume_offset: Number of records already processed before the current run.
        """
        total = self._total_processed(records_fetched, resume_offset)
        await self._save_checkpoint(total, operation="manual")

    @staticmethod
    def _total_processed(records_fetched: int, resume_offset: int) -> int:
        """Calculate total processed records including resume offset."""
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

    async def _save_checkpoint(self, total: int, *, operation: str) -> None:
        started_at = time.monotonic()
        try:
            await self._checkpoint_manager.save_checkpoint(total)
        except self._CHECKPOINT_SAVE_ERRORS:
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
