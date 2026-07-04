"""Persistence workflow for composite checkpoint state."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint._checkpoint_runtime import (
    CHECKPOINT_WRITE_ERRORS,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.exceptions import BioETLError, CheckpointConflictError

if TYPE_CHECKING:
    from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort, MetricsPort


class CompositeCheckpointPersistenceService:
    """Persist and clean up composite checkpoint files."""

    def __init__(
        self,
        *,
        composite_name: str,
        checkpoint_filename: str,
        glob_pattern: str,
        storage: CompositeCheckpointPort,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
    ) -> None:
        self._composite_name = composite_name
        self._checkpoint_filename = checkpoint_filename
        self._glob_pattern = glob_pattern
        self._storage = storage
        self._logger = logger
        self._metrics = metrics

    def _emit_checkpoint_saved_at_from_state(
        self,
        state: CompositeCheckpointState,
    ) -> None:
        """Publish persisted checkpoint freshness from state timestamps."""
        if self._metrics is None:
            return
        saved_at = state.updated_at or state.created_at
        if saved_at is None:
            return
        self._metrics.set_gauge(
            "bioetl_checkpoint_saved_at_seconds",
            saved_at.timestamp(),
            {"pipeline": self._composite_name},
        )

    def save(self, state: CompositeCheckpointState) -> None:
        """Save checkpoint state to JSON atomically."""
        try:
            self._storage.write_atomic(
                self._checkpoint_filename,
                json.dumps(state.to_dict(), indent=2),
            )
            self._logger.debug(
                "Saved checkpoint",
                composite=self._composite_name,
                checkpoint_path=self._checkpoint_filename,
                state=state.state.value,
                completed_enrichers=len(state.completed_enrichers),
            )
            self._emit_checkpoint_saved_at_from_state(state)
        except CHECKPOINT_WRITE_ERRORS as error:
            self._logger.error(
                "Failed to save checkpoint",
                composite=self._composite_name,
                error=str(error),
                error_type=type(error).__name__,
                reason_code="checkpoint_save_failed",
            )
            raise CheckpointConflictError(self._composite_name, str(error)) from error
        except BioETLError as error:
            self._logger.error(
                "Failed to save checkpoint",
                composite=self._composite_name,
                error=str(error),
                error_type=type(error).__name__,
                reason_code="unexpected_bioetl_error",
            )
            raise

    def delete(self) -> None:
        """Delete checkpoint file after successful completion."""
        if self._storage.delete(self._checkpoint_filename):
            self._logger.info(
                "Deleted checkpoint",
                composite=self._composite_name,
                checkpoint_path=self._checkpoint_filename,
            )

    def delete_orphaned(self) -> int:
        """Delete orphaned checkpoint files from previous runs."""
        deleted = 0
        for filename in self._storage.list_glob(self._glob_pattern):
            if filename == self._checkpoint_filename:
                continue
            if self._storage.delete(filename):
                self._logger.info(
                    "Deleted orphaned checkpoint",
                    composite=self._composite_name,
                    orphaned_checkpoint=filename,
                )
                deleted += 1
        return deleted

    def list_all(self) -> list[str]:
        """List all checkpoints for this composite pipeline."""
        return self._storage.list_glob(self._glob_pattern)
