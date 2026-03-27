"""Loading workflow for composite checkpoint state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint import _service_support as support
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState

if TYPE_CHECKING:
    from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort


class CompositeCheckpointLoadService:
    """Coordinate resume-vs-fresh checkpoint loading decisions."""

    def __init__(
        self,
        *,
        composite_name: str,
        run_id: str,
        storage: CompositeCheckpointPort,
        logger: LoggerPort,
        resume: bool,
        stale_threshold_hours: float,
        expected_context: support.ExpectedCheckpointContext,
        checkpoint_filename: str,
        glob_pattern: str,
    ) -> None:
        self._composite_name = composite_name
        self._run_id = run_id
        self._storage = storage
        self._logger = logger
        self._resume = resume
        self._stale_threshold_hours = stale_threshold_hours
        self._expected_context = expected_context
        self._checkpoint_filename = checkpoint_filename
        self._glob_pattern = glob_pattern

    def load(self) -> CompositeCheckpointState:
        """Load resumable state when available, otherwise return a fresh state."""
        if self._resume:
            resumed_state = self._load_resume_state()
            if resumed_state is not None:
                return resumed_state
        else:
            self._warn_if_overwrite_would_drop_progress()

        return support.fresh_checkpoint_state(
            composite_name=self._composite_name,
            run_id=self._run_id,
            anchors=self._expected_context,
        )

    def _load_resume_state(self) -> CompositeCheckpointState | None:
        filename = support.resolve_resume_checkpoint_filename(
            storage=self._storage,
            checkpoint_filename=self._checkpoint_filename,
            glob_pattern=self._glob_pattern,
        )
        if filename is None or not self._storage.exists(filename):
            return None

        state = support.load_checkpoint_state(
            storage=self._storage,
            logger=self._logger,
            composite_name=self._composite_name,
            filename=filename,
        )
        if state is None:
            return None

        support.validate_resume_compatibility(
            state=state,
            anchors=self._expected_context,
            logger=self._logger,
            composite_name=self._composite_name,
        )
        merged_state = support.merge_expected_anchors(state, self._expected_context)
        support.warn_if_checkpoint_stale(
            logger=self._logger,
            composite_name=self._composite_name,
            stale_threshold_hours=self._stale_threshold_hours,
            state=merged_state,
        )
        return merged_state

    def _warn_if_overwrite_would_drop_progress(self) -> None:
        support.warn_if_checkpoint_exists_with_progress(
            storage=self._storage,
            logger=self._logger,
            composite_name=self._composite_name,
            glob_pattern=self._glob_pattern,
        )
