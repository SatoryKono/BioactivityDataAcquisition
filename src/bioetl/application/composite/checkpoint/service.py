"""Composite checkpoint persistence service facade."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint import _service_support as support
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.exceptions import BioETLError, CheckpointConflictError, StorageError

if TYPE_CHECKING:
    from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort


class CompositeCheckpointService:
    """Thin facade for composite checkpoint persistence workflows."""

    _DEFAULT_STALE_THRESHOLD_HOURS: float = 24.0

    def __init__(
        self,
        composite_name: str,
        run_id: str,
        storage: CompositeCheckpointPort,
        logger: LoggerPort,
        resume: bool = False,
        stale_checkpoint_threshold_hours: float | None = None,
        expected_effective_config_hash: str | None = None,
        expected_contract_ref: str | None = None,
        expected_contract_version: str | None = None,
    ) -> None:
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
        self._expected_anchors = support.ExpectedCheckpointAnchors(
            effective_config_hash=expected_effective_config_hash or "",
            contract_ref=expected_contract_ref or "",
            contract_version=expected_contract_version or "",
            composite_run_identity=run_id,
        )
        self._checkpoint_filename = self._make_filename(run_id)

    def _make_filename(self, run_id: str) -> str:
        return f"composite_{self._composite_name}_{run_id}.json"

    def _glob_pattern(self) -> str:
        return f"composite_{self._composite_name}_*.json"

    async def load(self) -> CompositeCheckpointState:
        """Load checkpoint state or create a fresh one."""
        glob_pattern = self._glob_pattern()
        if self._resume:
            filename = support.resolve_resume_checkpoint_filename(
                storage=self._storage,
                checkpoint_filename=self._checkpoint_filename,
                glob_pattern=glob_pattern,
            )
            if filename is not None and self._storage.exists(filename):
                state = support.load_checkpoint_state(
                    storage=self._storage,
                    logger=self._logger,
                    composite_name=self._composite_name,
                    filename=filename,
                )
                if state is not None:
                    support.validate_resume_compatibility(
                        state=state,
                        anchors=self._expected_anchors,
                        logger=self._logger,
                        composite_name=self._composite_name,
                    )
                    state = support.merge_expected_anchors(
                        state, self._expected_anchors
                    )
                    support.warn_if_checkpoint_stale(
                        logger=self._logger,
                        composite_name=self._composite_name,
                        stale_threshold_hours=self._stale_threshold_hours,
                        state=state,
                    )
                    return state
        else:
            support.warn_if_checkpoint_exists_with_progress(
                storage=self._storage,
                logger=self._logger,
                composite_name=self._composite_name,
                glob_pattern=glob_pattern,
            )

        return support.fresh_checkpoint_state(
            composite_name=self._composite_name,
            run_id=self._run_id,
            anchors=self._expected_anchors,
        )

    async def save(self, state: CompositeCheckpointState) -> None:
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
        except support.CHECKPOINT_WRITE_ERRORS as error:
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

    async def delete(self) -> None:
        """Delete checkpoint file after successful completion."""
        if self._storage.delete(self._checkpoint_filename):
            self._logger.info(
                "Deleted checkpoint",
                composite=self._composite_name,
                checkpoint_path=self._checkpoint_filename,
            )

    async def delete_orphaned(self) -> int:
        """Delete orphaned checkpoint files from previous runs."""
        deleted = 0
        for filename in self._storage.list_glob(self._glob_pattern()):
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
        """List all checkpoints for this composite pipeline."""
        return self._storage.list_glob(self._glob_pattern())


CompositeCheckpointManager = CompositeCheckpointService
