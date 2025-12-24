"""Checkpoint Manager for ETL Pipelines.

This module is framework-agnostic and handles checkpoint persistence
for pipeline run tracking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.ports import CheckpointPort
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    import structlog


class CheckpointManager:
    """Framework-agnostic checkpoint management."""

    def __init__(
        self,
        checkpoint_port: CheckpointPort,
        logger: "structlog.BoundLogger",
        pipeline_name: str,
        run_id: RunID,
        resume: bool,
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            checkpoint_port: Port for checkpoint operations.
            logger: Logger instance.
            pipeline_name: Name of the pipeline.
            run_id: Unique identifier for the pipeline run.
            resume: Whether to resume from previous checkpoint.

        """
        self._checkpoint = checkpoint_port
        self._logger = logger
        self._pipeline_name = pipeline_name
        self._run_id = run_id
        self._resume = resume

    async def load_checkpoint(self) -> dict[str, Any] | None:
        """Load checkpoint if resuming."""
        if self._resume:
            checkpoint_data = await self._checkpoint.load(self._pipeline_name)
            if checkpoint_data:
                _, metadata = checkpoint_data
                self._logger.info(
                    "Found previous checkpoint",
                    extra={"metadata": metadata},
                )
                return metadata
        return None

    async def save_checkpoint(self, records_processed: int) -> None:
        """Save checkpoint.

        Args:
            records_processed: Count of records processed so far

        """
        await self._checkpoint.save(
            pipeline=self._pipeline_name,
            run_id=self._run_id,
            metadata={"records_processed": records_processed},
        )

    async def delete_checkpoint(self) -> None:
        """Delete checkpoint after successful run."""
        await self._checkpoint.delete(self._pipeline_name)
