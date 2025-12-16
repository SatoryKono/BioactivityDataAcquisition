"""Checkpoint Manager for ETL Pipelines.

This module is framework-agnostic. Prefect integration is provided by
the orchestration layer (bioetl.orchestration.tasks).
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from bioetl.domain.ports import CheckpointPort
from bioetl.domain.types import RunID, Watermark

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
        watermark_extractor: Callable[[dict[str, Any]], Watermark],
    ) -> None:
        self._checkpoint = checkpoint_port
        self._logger = logger
        self._pipeline_name = pipeline_name
        self._run_id = run_id
        self._resume = resume
        self._extract_watermark = watermark_extractor

    async def load_checkpoint(self) -> Watermark | None:
        """Load checkpoint if resuming."""
        if self._resume:
            checkpoint_data = await self._checkpoint.load(self._pipeline_name)
            if checkpoint_data:
                watermark, _, metadata = checkpoint_data
                self._logger.info(
                    f"Resuming from checkpoint: {watermark}",
                    extra={"metadata": metadata},
                )
                return watermark
        return None

    async def save_checkpoint(
        self, last_record: dict[str, Any], records_processed: int
    ) -> None:
        """Save checkpoint.

        Args:
            last_record: The last processed record (used to extract watermark)
            records_processed: Count of records processed so far
        """
        watermark = self._extract_watermark(last_record)
        await self._checkpoint.save(
            pipeline=self._pipeline_name,
            watermark=watermark,
            run_id=self._run_id,
            metadata={"records_processed": records_processed},
        )

    async def delete_checkpoint(self) -> None:
        """Delete checkpoint after successful run."""
        await self._checkpoint.delete(self._pipeline_name)
