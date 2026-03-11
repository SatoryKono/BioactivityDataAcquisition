"""Composite checkpoint persistence service.

Delegates all filesystem I/O to a CompositeCheckpointPort adapter,
keeping the application layer free of direct Path/glob/read/write operations.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.exceptions import BioETLError, CheckpointConflictError, StorageError

if TYPE_CHECKING:
    from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort

_CHECKPOINT_READ_ERRORS = (
    json.JSONDecodeError,
    OSError,
    TypeError,
    ValueError,
    StorageError,
)
_CHECKPOINT_WRITE_ERRORS = (
    OSError,
    TypeError,
    ValueError,
    StorageError,
)


class CompositeCheckpointService:
    """Manages checkpoint persistence for composite pipelines."""

    def __init__(
        self,
        composite_name: str,
        run_id: str,
        storage: CompositeCheckpointPort,
        logger: LoggerPort,
        resume: bool = False,
    ) -> None:
        self._composite_name = composite_name
        self._run_id = run_id
        self._storage = storage
        self._logger = logger
        self._resume = resume
        self._checkpoint_filename = self._make_filename(run_id)

    def _make_filename(self, run_id: str) -> str:
        return f"composite_{self._composite_name}_{run_id}.json"

    def _glob_pattern(self) -> str:
        return f"composite_{self._composite_name}_*.json"

    def _get_latest_checkpoint_filename(self) -> str | None:
        matches = self._storage.list_glob(self._glob_pattern())
        return matches[0] if matches else None

    def _warn_if_checkpoint_exists_with_progress(self) -> None:
        latest = self._get_latest_checkpoint_filename()
        if latest is None:
            return
        if not self._storage.exists(latest):
            return

        try:
            content = self._storage.read(latest)
            if content is None:
                return
            data = json.loads(content)
            state = CompositeCheckpointState.from_dict(data)
            if state.is_resumable:
                self._logger.warning(
                    "Existing checkpoint with progress will be overwritten",
                    composite=self._composite_name,
                    checkpoint_path=latest,
                    checkpoint_state=state.state.value,
                    seed_completed=state.seed_completed,
                    completed_enrichers=len(state.completed_enrichers),
                    hint="Use --resume flag to continue from previous progress",
                )
        except _CHECKPOINT_READ_ERRORS as e:
            self._logger.debug(
                "Checkpoint exists but cannot be parsed, will be overwritten",
                composite=self._composite_name,
                checkpoint_path=latest,
                error=str(e),
                error_type=type(e).__name__,
                reason_code="checkpoint_read_failed",
            )
        except BioETLError as e:
            self._logger.warning(
                "Checkpoint pre-check failed with domain error",
                composite=self._composite_name,
                checkpoint_path=latest,
                error=str(e),
                error_type=type(e).__name__,
                reason_code="unexpected_bioetl_error",
            )

    def _resolve_resume_checkpoint_filename(self) -> str | None:
        if self._storage.exists(self._checkpoint_filename):
            return self._checkpoint_filename
        return self._get_latest_checkpoint_filename()

    def _load_checkpoint_state(
        self,
        filename: str,
    ) -> CompositeCheckpointState | None:
        try:
            content = self._storage.read(filename)
            if content is None:
                return None
            data = json.loads(content)
            state = CompositeCheckpointState.from_dict(data)
            raw_state = data.get("state")
            if raw_state is not None and state.state.value != raw_state:
                self._logger.warning(
                    "Checkpoint state value corrupted, using default",
                    composite=self._composite_name,
                    raw_state=raw_state,
                    parsed_state=state.state.value,
                )
            self._logger.info(
                "Loaded checkpoint",
                composite=self._composite_name,
                checkpoint_path=filename,
                state=state.state.value,
                seed_completed=state.seed_completed,
                completed_enrichers=list(state.completed_enrichers),
            )
            return state
        except _CHECKPOINT_READ_ERRORS as e:
            self._logger.warning(
                "Failed to load checkpoint",
                composite=self._composite_name,
                error=str(e),
                error_type=type(e).__name__,
                reason_code="checkpoint_load_failed",
            )
        except BioETLError as e:
            self._logger.warning(
                "Failed to load checkpoint",
                composite=self._composite_name,
                error=str(e),
                error_type=type(e).__name__,
                reason_code="unexpected_bioetl_error",
            )
        return None

    async def load(self) -> CompositeCheckpointState:
        """Load checkpoint state or create a fresh one.

        Returns:
            Existing checkpoint state if resume mode and a valid checkpoint file exists,
            otherwise a fresh CompositeCheckpointState with NOT_STARTED status.
        """
        if self._resume:
            filename = self._resolve_resume_checkpoint_filename()
            if filename is not None and self._storage.exists(filename):
                state = self._load_checkpoint_state(filename)
                if state is not None:
                    return state
        else:
            self._warn_if_checkpoint_exists_with_progress()

        return CompositeCheckpointState(
            composite_name=self._composite_name,
            run_id=self._run_id,
            created_at=datetime.now(tz=UTC),
        )

    async def save(self, state: CompositeCheckpointState) -> None:
        """Save checkpoint state to JSON atomically.

        Args:
            state: Current checkpoint state to persist.
        """
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
        except _CHECKPOINT_WRITE_ERRORS as e:
            self._logger.error(
                "Failed to save checkpoint",
                composite=self._composite_name,
                error=str(e),
                error_type=type(e).__name__,
                reason_code="checkpoint_save_failed",
            )
            raise CheckpointConflictError(self._composite_name, str(e)) from e
        except BioETLError as e:
            self._logger.error(
                "Failed to save checkpoint",
                composite=self._composite_name,
                error=str(e),
                error_type=type(e).__name__,
                reason_code="unexpected_bioetl_error",
            )
            raise

    async def delete(self) -> None:
        """Delete checkpoint file after successful completion."""
        deleted = self._storage.delete(self._checkpoint_filename)
        if deleted:
            self._logger.info(
                "Deleted checkpoint",
                composite=self._composite_name,
                checkpoint_path=self._checkpoint_filename,
            )

    async def list_all(self) -> list[str]:
        """List all checkpoints for this composite pipeline.

        Returns:
            List of checkpoint filenames matching this composite name.
        """
        return self._storage.list_glob(self._glob_pattern())


CompositeCheckpointManager = CompositeCheckpointService
