"""Checkpoint and recovery service for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchCheckpointRecoveryService"]


from typing import TYPE_CHECKING

from bioetl.application.core.batch_runtime_failure_policy import OPERATION_ERRORS

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.domain.ports import LoggerPort


class BatchCheckpointRecoveryService:
    """Owns checkpoint save semantics for runtime, shutdown, and recovery."""

    _CHECKPOINT_SAVE_ERRORS = OPERATION_ERRORS

    def __init__(
        self,
        *,
        checkpoint_manager: CheckpointManagerService,
        logger: LoggerPort,
    ) -> None:
        self._checkpoint_manager = checkpoint_manager
        self._logger = logger

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
        await self._checkpoint_manager.save_checkpoint(total)

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
                return
            await self._checkpoint_manager.save_checkpoint(total)
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
            await self._checkpoint_manager.save_checkpoint(total)
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
        await self._checkpoint_manager.save_checkpoint(total)

    @staticmethod
    def _total_processed(records_fetched: int, resume_offset: int) -> int:
        """Calculate total processed records including resume offset."""
        return resume_offset + records_fetched
