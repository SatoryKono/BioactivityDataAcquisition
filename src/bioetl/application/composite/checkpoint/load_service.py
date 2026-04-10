"""Loading workflow for composite checkpoint state."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint import _service_support as support
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.control_plane.run_ledger import project_run_ledger_replay
from bioetl.domain.exceptions import CheckpointConflictError

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        CompositeCheckpointPort,
        LoggerPort,
        MetricsPort,
        RunLedgerPort,
    )


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
        run_ledger_port: RunLedgerPort | None = None,
        metrics: MetricsPort | None = None,
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
        self._run_ledger_port = run_ledger_port
        self._metrics = metrics

    def _emit_checkpoint_load_status(self, status: str) -> None:
        """Emit bounded composite checkpoint load outcome."""
        if self._metrics is None:
            return
        self._metrics.increment_counter(
            "checkpoint_load_events_total",
            1,
            {
                "pipeline": self._composite_name,
                "status": status,
            },
        )

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
            self._emit_checkpoint_load_status("missing")
            return None

        state = support.load_checkpoint_state(
            storage=self._storage,
            logger=self._logger,
            composite_name=self._composite_name,
            filename=filename,
            metrics=self._metrics,
        )
        if state is None:
            return None

        try:
            support.validate_resume_compatibility(
                state=state,
                anchors=self._expected_context,
                logger=self._logger,
                composite_name=self._composite_name,
            )
        except CheckpointConflictError:
            self._emit_checkpoint_load_status("incompatible")
            raise
        merged_state = support.merge_expected_anchors(state, self._expected_context)
        replayed_state = self._replay_checkpoint_suffix(merged_state)
        support.warn_if_checkpoint_stale(
            logger=self._logger,
            composite_name=self._composite_name,
            stale_threshold_hours=self._stale_threshold_hours,
            state=replayed_state,
        )
        return replayed_state

    def _warn_if_overwrite_would_drop_progress(self) -> None:
        support.warn_if_checkpoint_exists_with_progress(
            storage=self._storage,
            logger=self._logger,
            composite_name=self._composite_name,
            glob_pattern=self._glob_pattern,
        )

    def _replay_checkpoint_suffix(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState:
        if self._run_ledger_port is None:
            return state
        if not state.manifest_id:
            return state

        try:
            replay_entries = self._run_ledger_port.list_entries_after(
                state.manifest_id,
                state.last_event_id,
            )
        except ValueError as error:
            detail = (
                f"checkpoint replay watermark {state.last_event_id!r} is missing "
                f"for manifest {state.manifest_id!r}"
            )
            raise CheckpointConflictError(self._composite_name, detail) from error

        if not replay_entries:
            return state

        replay_projection = project_run_ledger_replay(replay_entries)
        replayed_state = replace(
            state,
            state=(
                replay_projection.state
                if replay_projection.state is not None
                else state.state
            ),
            seed_completed=(
                replay_projection.seed_completed
                if replay_projection.seed_completed is not None
                else state.seed_completed
            ),
            merge_completed=(
                replay_projection.merge_completed
                if replay_projection.merge_completed is not None
                else state.merge_completed
            ),
            last_event_id=replay_projection.last_event_id,
            last_event_occurred_at=replay_projection.last_event_occurred_at,
        )
        self._logger.info(
            "Replayed checkpoint state from run ledger",
            composite=self._composite_name,
            manifest_id=state.manifest_id,
            replayed_event_count=replay_projection.replayed_entry_count,
            replay_start_event_id=state.last_event_id,
            replay_end_event_id=replayed_state.last_event_id,
            replay_end_occurred_at=(
                replayed_state.last_event_occurred_at.isoformat()
                if replayed_state.last_event_occurred_at is not None
                else None
            ),
            replay_end_state=replayed_state.state.value,
            replay_seed_completed=replayed_state.seed_completed,
            replay_merge_completed=replayed_state.merge_completed,
        )
        return replayed_state
