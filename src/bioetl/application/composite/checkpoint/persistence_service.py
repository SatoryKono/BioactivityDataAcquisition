"""Persistence workflow for composite checkpoint state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint._checkpoint_runtime import (
    CHECKPOINT_WRITE_ERRORS,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.exceptions import BioETLError, CheckpointConflictError

if TYPE_CHECKING:
    from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort, MetricsPort


@dataclass(frozen=True, slots=True)
class CompositeCheckpointPersistenceParams:
    """Collaborator bag for :class:`CompositeCheckpointPersistenceService`."""

    composite_name: str
    checkpoint_filename: str
    glob_pattern: str
    storage: CompositeCheckpointPort
    logger: LoggerPort
    metrics: MetricsPort | None = None


class CompositeCheckpointPersistenceService:
    """Persist and clean up composite checkpoint files."""

    def __init__(self, params: CompositeCheckpointPersistenceParams) -> None:
        self._composite_name = params.composite_name
        self._checkpoint_filename = params.checkpoint_filename
        self._glob_pattern = params.glob_pattern
        self._storage = params.storage
        self._logger = params.logger
        self._metrics = params.metrics

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
            content = json.dumps(state.to_dict(), indent=2)
            self._save_history(state, content)
            self._storage.write_atomic(
                self._checkpoint_filename,
                content,
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

    def _save_history(self, state: CompositeCheckpointState, content: str) -> None:
        """Keep manifest-bound evidence after the mutable resume file is deleted."""
        if not state.manifest_id:
            return
        for component in (state.composite_name, state.run_id, state.manifest_id):
            if (
                not component
                or component in {".", ".."}
                or any(char in component for char in "/\\:")
            ):
                raise ValueError("Invalid composite checkpoint history identity")
        digest = sha256(content.encode("utf-8")).hexdigest()
        history_path = (
            f".history/by_pipeline/{state.composite_name}/{state.run_id}/{digest}.json"
        )
        self._storage.write_atomic(history_path, content)
        self._storage.write_atomic(
            f".history/by_manifest/{state.manifest_id}.json",
            json.dumps(
                {
                    "manifest_id": state.manifest_id,
                    "pipeline": state.composite_name,
                    "run_id": state.run_id,
                    "history_path": history_path,
                }
            ),
        )

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
