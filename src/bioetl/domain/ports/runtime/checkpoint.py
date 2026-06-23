"""Checkpoint port for pipeline state persistence.

This port allows pipelines to save and load their state, enabling
resilience and run tracking.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.types import MetaDict, RunID

__all__ = [
    "CheckpointPort",
]


@runtime_checkable
class CheckpointPort(Protocol):
    """Port for pipeline checkpointing.

    This interface allows pipelines to save and load their state, enabling
    resilience and run tracking.
    """

    async def save(
        self,
        pipeline: str,
        run_id: RunID,
        metadata: MetaDict,
    ) -> None:
        """Save a checkpoint.

        Args:
            pipeline: The name of the pipeline.
            run_id: The ID of the run creating the checkpoint.
            metadata: Additional metadata to store with the checkpoint.
        """
        ...

    async def load(
        self,
        pipeline: str,
    ) -> tuple[RunID, MetaDict] | None:
        """Load a checkpoint.

        Args:
            pipeline: The name of the pipeline.

        Returns:
            A tuple containing the run ID and metadata, or None
            if no checkpoint is found.
        """
        ...

    async def load_for_run(
        self,
        pipeline: str,
        run_id: RunID,
    ) -> tuple[RunID, MetaDict] | None:
        """Load immutable checkpoint evidence for one specific run occurrence."""
        ...

    async def load_for_manifest_id(
        self,
        manifest_id: str,
    ) -> tuple[RunID, MetaDict] | None:
        """Load immutable checkpoint evidence for one specific manifest."""
        ...

    async def list_all(self) -> list[str]:
        """List all pipelines that have checkpoints.

        Returns:
            A list of pipeline names.
        """
        ...

    async def delete(self, pipeline: str) -> None:
        """Delete a checkpoint.

        Args:
            pipeline: The name of the pipeline whose checkpoint should be deleted.
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the checkpoint connection and release resources."""
        ...
