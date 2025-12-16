"""Checkpoint Manager for ETL Pipelines."""

from typing import TYPE_CHECKING

from prefect import task

from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.application.pipeline.base import BasePipeline


class CheckpointManager:
    """Manages saving, loading, and deleting checkpoints."""

    def __init__(self, pipeline: "BasePipeline"):
        self.pipeline = pipeline

    @task(name="Load Checkpoint")
    async def load_checkpoint(self) -> Watermark | None:
        """Load checkpoint if resuming."""
        if self.pipeline.resume:
            checkpoint_data = self.pipeline.checkpoint.load(self.pipeline.pipeline_name)
            if checkpoint_data:
                watermark, _, metadata = checkpoint_data
                self.pipeline.logger.info(
                    f"Resuming from checkpoint: {watermark}",
                    extra={"metadata": metadata},
                )
                return watermark
        return None

    async def save_checkpoint(self, last_record: dict) -> None:
        """Save checkpoint."""
        watermark = self.pipeline.extract_watermark(last_record)
        self.pipeline.checkpoint.save(
            pipeline=self.pipeline.pipeline_name,
            watermark=watermark,
            run_id=self.pipeline.run_id,
            metadata={"records_processed": self.pipeline.executor.records_fetched},
        )

    @task(name="Delete Checkpoint")
    async def delete_checkpoint(self) -> None:
        """Delete checkpoint after successful run."""
        self.pipeline.checkpoint.delete(self.pipeline.pipeline_name)
