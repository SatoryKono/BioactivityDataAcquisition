"""Composite checkpoint persistence service."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.exceptions import BioETLError, CheckpointConflictError, StorageError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

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
        checkpoint_dir: Path,
        logger: LoggerPort,
        resume: bool = False,
    ) -> None:
        self._composite_name = composite_name
        self._run_id = run_id
        self._checkpoint_dir = checkpoint_dir
        self._logger = logger
        self._resume = resume
        self._checkpoint_path = self._get_checkpoint_path()

    def _get_checkpoint_path(self) -> Path:
        filename = f"composite_{self._composite_name}_{self._run_id}.json"
        return self._checkpoint_dir / filename

    def _get_latest_checkpoint_path(self) -> Path | None:
        pattern = f"composite_{self._composite_name}_*.json"
        checkpoints = list(self._checkpoint_dir.glob(pattern))
        if not checkpoints:
            return None
        return max(checkpoints, key=lambda p: p.stat().st_mtime)

    def _warn_if_checkpoint_exists_with_progress(self) -> None:
        checkpoint_path = self._get_latest_checkpoint_path()
        if checkpoint_path is None or not checkpoint_path.exists():
            return

        try:
            data = json.loads(checkpoint_path.read_text())
            state = CompositeCheckpointState.from_dict(data)
            if state.is_resumable:
                self._logger.warning(
                    "Existing checkpoint with progress will be overwritten",
                    composite=self._composite_name,
                    checkpoint_path=str(checkpoint_path),
                    checkpoint_state=state.state.value,
                    seed_completed=state.seed_completed,
                    completed_enrichers=len(state.completed_enrichers),
                    hint="Use --resume flag to continue from previous progress",
                )
        except _CHECKPOINT_READ_ERRORS as e:
            self._logger.debug(
                "Checkpoint exists but cannot be parsed, will be overwritten",
                composite=self._composite_name,
                checkpoint_path=str(checkpoint_path),
                error=str(e),
                error_type=type(e).__name__,
                reason_code="checkpoint_read_failed",
            )
        except BioETLError as e:
            self._logger.warning(
                "Checkpoint pre-check failed with domain error",
                composite=self._composite_name,
                checkpoint_path=str(checkpoint_path),
                error=str(e),
                error_type=type(e).__name__,
                reason_code="unexpected_bioetl_error",
            )

    def _resolve_resume_checkpoint_path(self) -> Path | None:
        if self._checkpoint_path.exists():
            return self._checkpoint_path
        return self._get_latest_checkpoint_path()

    def _load_checkpoint_state(
        self,
        checkpoint_path: Path,
    ) -> CompositeCheckpointState | None:
        try:
            data = json.loads(checkpoint_path.read_text())
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
                checkpoint_path=str(checkpoint_path),
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
        """Load checkpoint state or create a fresh one."""
        if self._resume:
            checkpoint_path = self._resolve_resume_checkpoint_path()
            if checkpoint_path is not None and checkpoint_path.exists():
                state = self._load_checkpoint_state(checkpoint_path)
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
        """Save checkpoint state to JSON atomically."""
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        temp_path = self._checkpoint_path.with_suffix(".tmp")
        try:
            temp_path.write_text(json.dumps(state.to_dict(), indent=2))
            temp_path.replace(self._checkpoint_path)
            self._logger.debug(
                "Saved checkpoint",
                composite=self._composite_name,
                checkpoint_path=str(self._checkpoint_path),
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
            if temp_path.exists():
                temp_path.unlink()
            raise CheckpointConflictError(self._composite_name, str(e)) from e
        except BioETLError as e:
            self._logger.error(
                "Failed to save checkpoint",
                composite=self._composite_name,
                error=str(e),
                error_type=type(e).__name__,
                reason_code="unexpected_bioetl_error",
            )
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def delete(self) -> None:
        """Delete checkpoint file after successful completion."""
        if self._checkpoint_path.exists():
            self._checkpoint_path.unlink()
            self._logger.info(
                "Deleted checkpoint",
                composite=self._composite_name,
                checkpoint_path=str(self._checkpoint_path),
            )

    async def list_all(self) -> list[Path]:
        """List all checkpoints for this composite pipeline."""
        pattern = f"composite_{self._composite_name}_*.json"
        return list(self._checkpoint_dir.glob(pattern))


CompositeCheckpointManager = CompositeCheckpointService
