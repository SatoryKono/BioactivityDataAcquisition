"""Checkpoint management for ETL pipelines.

Handles checkpoint save, load, and delete operations.
"""

from typing import TYPE_CHECKING

from prefect import task

from bioetl.domain.ports import CheckpointPort
from bioetl.domain.types import RunID, Watermark

if TYPE_CHECKING:
    from bioetl.infrastructure.observability.logging import PipelineLogger


class PipelineCheckpointManager:
    """Manages checkpoints for pipeline resumability.

    Handles:
    - Checkpoint loading on resume
    - Periodic checkpoint saving
    - Checkpoint cleanup on completion
    """

    def __init__(
        self,
        checkpoint: CheckpointPort,
        pipeline_name: str,
        run_id: RunID,
        logger: "PipelineLogger",
    ) -> None:
        self.checkpoint = checkpoint
        self.pipeline_name = pipeline_name
        self.run_id = run_id
        self.logger = logger

    @task(name="Load Checkpoint")
    async def load(self, resume: bool) -> Watermark | None:
        """Load checkpoint if resuming."""
        if resume:
            checkpoint_data = self.checkpoint.load(self.pipeline_name)
            if checkpoint_data:
                watermark, _, metadata = checkpoint_data
                self.logger.info(
                    f"Resuming from checkpoint: {watermark}",
                    extra={"metadata": metadata},
                )
                return watermark
        return None

    async def save(
        self, watermark: Watermark, records_processed: int
    ) -> None:
        """Save checkpoint with current progress."""
        self.checkpoint.save(
            pipeline=self.pipeline_name,
            watermark=watermark,
            run_id=self.run_id,
            metadata={"records_processed": records_processed},
        )

    @task(name="Delete Checkpoint")
    async def delete(self) -> None:
        """Delete checkpoint on successful completion."""
        self.checkpoint.delete(self.pipeline_name)
