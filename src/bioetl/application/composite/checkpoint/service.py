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

    _DEFAULT_STALE_THRESHOLD_HOURS: float = 24.0

    def __init__(
        self,
        composite_name: str,
        run_id: str,
        storage: CompositeCheckpointPort,
        logger: LoggerPort,
        resume: bool = False,
        stale_checkpoint_threshold_hours: float | None = None,
    ) -> None:
        """Initialize the composite checkpoint service.

        Args:
            composite_name: Logical name of the composite pipeline, used to
                scope checkpoint filenames and log entries.
            run_id: Unique identifier for the current run, embedded in the
                checkpoint filename to distinguish parallel executions.
            storage: Port adapter that handles all filesystem I/O (read,
                write, list, delete) for checkpoint files.
            logger: Structured logger for progress and diagnostic output.
            resume: When ``True``, ``load()`` will attempt to locate and
                deserialise an existing checkpoint file and return its state
                instead of creating a fresh one. When ``False`` (default),
                ``load()`` always starts from a clean state and emits a
                warning if a checkpoint with prior progress would be silently
                overwritten.
        """
        self._composite_name = composite_name
        self._run_id = run_id
        self._storage = storage
        self._logger = logger
        self._resume = resume
        self._stale_threshold_hours = (
            stale_checkpoint_threshold_hours
            if stale_checkpoint_threshold_hours is not None
            else self._DEFAULT_STALE_THRESHOLD_HOURS
        )
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

    def _warn_if_checkpoint_stale(self, state: CompositeCheckpointState) -> None:
        """Emit a warning if the checkpoint is older than the staleness threshold."""
        if self._stale_threshold_hours <= 0:
            return
        ref_time = state.updated_at or state.created_at
        if ref_time is None:
            return
        age = datetime.now(tz=UTC) - ref_time
        threshold_seconds = self._stale_threshold_hours * 3600
        if age.total_seconds() > threshold_seconds:
            self._logger.warning(
                "Resuming from stale checkpoint",
                composite=self._composite_name,
                checkpoint_age_hours=round(age.total_seconds() / 3600, 1),
                threshold_hours=self._stale_threshold_hours,
                checkpoint_updated_at=ref_time.isoformat(),
                checkpoint_state=state.state.value,
                reason_code="stale_checkpoint_resume",
                hint="Seed data may have been overwritten since this checkpoint was saved",
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
                    self._warn_if_checkpoint_stale(state)
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

    async def delete_orphaned(self) -> int:
        """Delete orphaned checkpoint files from previous runs.

        Returns:
            Number of orphaned checkpoints deleted.
        """
        all_files = self._storage.list_glob(self._glob_pattern())
        deleted = 0
        for filename in all_files:
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

    async def list_all(self) -> list[str]:
        """List all checkpoints for this composite pipeline.

        Returns:
            List of checkpoint filenames matching this composite name.
        """
        return self._storage.list_glob(self._glob_pattern())


CompositeCheckpointManager = CompositeCheckpointService
