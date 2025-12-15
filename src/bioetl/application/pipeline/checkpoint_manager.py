"""Checkpoint manager for ETL pipelines.

Handles checkpoint save, load, and delete operations for resumable pipelines.
"""

from logging import Logger

from bioetl.domain.ports import CheckpointPort
from bioetl.domain.types import RunID, Watermark


class CheckpointManager:
    """Manages checkpoint lifecycle for pipelines.

    Responsibilities:
    - Load checkpoint for resume functionality
    - Save periodic checkpoints during execution
    - Delete checkpoint on successful completion
    """

    def __init__(
        self,
        checkpoint: CheckpointPort,
        pipeline_name: str,
        run_id: RunID,
        logger: Logger,
    ) -> None:
        self._checkpoint = checkpoint
        self._pipeline_name = pipeline_name
        self._run_id = run_id
        self._logger = logger

    def load(self, resume: bool) -> Watermark | None:
        """Load checkpoint if resume mode is enabled.

        Args:
            resume: Whether to attempt loading checkpoint

        Returns:
            Watermark from checkpoint or None
        """
        if not resume:
            return None

        checkpoint_data = self._checkpoint.load(self._pipeline_name)
        if checkpoint_data:
            watermark, _, metadata = checkpoint_data
            self._logger.info(
                f"Resuming from checkpoint: {watermark}",
                extra={"metadata": metadata},
            )
            return watermark
        return None

    def save(self, watermark: Watermark, records_processed: int) -> None:
        """Save checkpoint with current progress.

        Args:
            watermark: Current position watermark
            records_processed: Number of records processed
        """
        self._checkpoint.save(
            pipeline=self._pipeline_name,
            watermark=watermark,
            run_id=self._run_id,
            metadata={"records_processed": records_processed},
        )

    def delete(self) -> None:
        """Delete checkpoint after successful completion."""
        self._checkpoint.delete(self._pipeline_name)
