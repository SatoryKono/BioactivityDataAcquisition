"""Checkpoint service for administrative operations (Application layer).

Provides high-level checkpoint management for CLI and other interfaces.
Uses CheckpointPort for actual persistence operations.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import CheckpointPort, LoggerPort


@dataclass(frozen=True, slots=True)
class CheckpointInfo:
    """Information about a checkpoint.

    Attributes:
        pipeline_name: Name of the pipeline.
        run_id: Run ID that created this checkpoint.
        metadata: Checkpoint metadata (records_processed, etc.).
    """

    pipeline_name: str
    run_id: str | None
    metadata: dict[str, Any]


@dataclass
class CheckpointService:
    """Service for administrative checkpoint operations.

    Provides high-level operations for checkpoint management
    used by CLI and other interfaces. Wraps CheckpointPort
    for Application-layer abstraction.

    Attributes:
        checkpoint_port: Port for checkpoint persistence.
        logger: Structured logger for observability.

    Example:
        >>> service = CheckpointService(checkpoint_port=port, logger=logger)
        >>> checkpoints = await service.list_checkpoints()
        >>> for cp in checkpoints:
        ...     print(f"{cp.pipeline_name}: {cp.metadata}")
    """

    checkpoint_port: CheckpointPort
    logger: LoggerPort

    async def list_checkpoints(self) -> list[CheckpointInfo]:
        """List all checkpoints across all pipelines.

        Returns:
            List of CheckpointInfo with pipeline names and metadata.
        """
        self.logger.debug("Listing all checkpoints")

        pipeline_names = await self.checkpoint_port.list_all()
        checkpoints: list[CheckpointInfo] = []

        for pipeline_name in pipeline_names:
            checkpoint_data = await self.checkpoint_port.load(pipeline_name)
            if checkpoint_data:
                run_id, metadata = checkpoint_data
                checkpoints.append(
                    CheckpointInfo(
                        pipeline_name=pipeline_name,
                        run_id=str(run_id),
                        metadata=metadata,
                    )
                )
            else:
                # Checkpoint exists but couldn't be loaded
                checkpoints.append(
                    CheckpointInfo(
                        pipeline_name=pipeline_name,
                        run_id=None,
                        metadata={},
                    )
                )

        self.logger.info(
            "Listed checkpoints",
            checkpoint_count=len(checkpoints),
        )

        return checkpoints

    async def get_checkpoint(self, pipeline_name: str) -> CheckpointInfo | None:
        """Get checkpoint for a specific pipeline.

        Args:
            pipeline_name: Name of the pipeline.

        Returns:
            CheckpointInfo if checkpoint exists, None otherwise.
        """
        self.logger.debug("Getting checkpoint", pipeline=pipeline_name)

        checkpoint_data = await self.checkpoint_port.load(pipeline_name)
        if checkpoint_data is None:
            self.logger.debug("Checkpoint not found", pipeline=pipeline_name)
            return None

        run_id, metadata = checkpoint_data
        self.logger.info(
            "Got checkpoint",
            pipeline=pipeline_name,
            run_id=str(run_id),
        )

        return CheckpointInfo(
            pipeline_name=pipeline_name,
            run_id=str(run_id),
            metadata=metadata,
        )

    async def delete_checkpoint(self, pipeline_name: str) -> bool:
        """Delete checkpoint for a specific pipeline.

        Args:
            pipeline_name: Name of the pipeline.

        Returns:
            True if checkpoint was deleted, False if it didn't exist.
        """
        self.logger.debug("Deleting checkpoint", pipeline=pipeline_name)

        # Check if checkpoint exists first
        existing = await self.checkpoint_port.load(pipeline_name)
        if existing is None:
            self.logger.debug(
                "Checkpoint not found for deletion", pipeline=pipeline_name
            )
            return False

        await self.checkpoint_port.delete(pipeline_name)
        self.logger.info("Deleted checkpoint", pipeline=pipeline_name)

        return True

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.checkpoint_port.aclose()
