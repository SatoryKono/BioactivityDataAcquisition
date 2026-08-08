"""Loading workflow for composite checkpoint state."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.composite.checkpoint._anchor_context import (
    ExpectedCheckpointContext,
    fresh_checkpoint_state,
    merge_expected_anchors,
)
from bioetl.application.composite.checkpoint._checkpoint_replay_projection import (
    ensure_projection_coverage,
    log_rich_checkpoint_projection,
    merge_replay_projection_state,
)
from bioetl.application.composite.checkpoint._checkpoint_runtime import (
    load_checkpoint_state,
    resolve_resume_checkpoint_filename,
)
from bioetl.application.composite.checkpoint._checkpoint_warnings import (
    warn_if_checkpoint_exists_with_progress,
    warn_if_checkpoint_stale,
)
from bioetl.application.composite.checkpoint._load_validation import (
    validate_resume_compatibility,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.control_plane.run_ledger import (
    RunLedgerReplayProjection,
    project_run_ledger_replay,
)
from bioetl.domain.exceptions import CheckpointConflictError
from bioetl.domain.ports import (
    ClockPort,
    CompositeCheckpointPort,
    LoggerPort,
    MetricsPort,
    RunLedgerPort,
)


@dataclass(frozen=True, slots=True)
class CompositeCheckpointLoadParams:
    """Collaborator bag for :class:`CompositeCheckpointLoadService`."""

    composite_name: str
    run_id: str
    storage: CompositeCheckpointPort
    logger: LoggerPort
    resume: bool
    stale_threshold_hours: float
    expected_context: ExpectedCheckpointContext
    checkpoint_filename: str
    glob_pattern: str
    run_ledger_port: RunLedgerPort | None = None
    metrics: MetricsPort | None = None
    clock: ClockPort | None = None


class CompositeCheckpointLoadService:
    """Coordinate resume-vs-fresh checkpoint loading decisions."""

    def __init__(self, params: CompositeCheckpointLoadParams) -> None:
        self._composite_name = params.composite_name
        self._run_id = params.run_id
        self._storage = params.storage
        self._logger = params.logger
        self._resume = params.resume
        self._stale_threshold_hours = params.stale_threshold_hours
        self._expected_context = params.expected_context
        self._checkpoint_filename = params.checkpoint_filename
        self._glob_pattern = params.glob_pattern
        self._run_ledger_port = params.run_ledger_port
        self._metrics = params.metrics
        self._clock = params.clock

    def _emit_checkpoint_load_status(self, status: str) -> None:
        """Emit bounded composite checkpoint load outcome."""
        if self._metrics is None:
            return
        self._metrics.increment_counter(
            "bioetl_checkpoint_load_events_total",
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

        return fresh_checkpoint_state(
            composite_name=self._composite_name,
            run_id=self._run_id,
            anchors=self._expected_context,
            clock=self._clock,
        )

    def _load_resume_state(self) -> CompositeCheckpointState | None:
        filename = resolve_resume_checkpoint_filename(
            storage=self._storage,
            checkpoint_filename=self._checkpoint_filename,
            glob_pattern=self._glob_pattern,
        )
        if filename is None or not self._storage.exists(filename):
            self._emit_checkpoint_load_status("missing")
            return None

        state: CompositeCheckpointState | None = load_checkpoint_state(
            storage=self._storage,
            logger=self._logger,
            composite_name=self._composite_name,
            filename=filename,
            metrics=self._metrics,
        )
        if state is None:
            return None

        try:
            validate_resume_compatibility(
                state=state,
                anchors=self._expected_context,
                logger=self._logger,
                composite_name=self._composite_name,
            )
        except CheckpointConflictError:
            self._emit_checkpoint_load_status("incompatible")
            raise
        merged_state: CompositeCheckpointState = merge_expected_anchors(
            state,
            self._expected_context,
        )
        replayed_state: CompositeCheckpointState = self._replay_checkpoint_suffix(
            merged_state
        )
        warn_if_checkpoint_stale(
            logger=self._logger,
            composite_name=self._composite_name,
            stale_threshold_hours=self._stale_threshold_hours,
            state=replayed_state,
            clock=self._clock,
        )
        return replayed_state

    def _warn_if_overwrite_would_drop_progress(self) -> None:
        warn_if_checkpoint_exists_with_progress(
            storage=self._storage,
            logger=self._logger,
            composite_name=self._composite_name,
            glob_pattern=self._glob_pattern,
            metrics=self._metrics,
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
            self._emit_checkpoint_load_status("replay_conflict")
            detail = (
                f"checkpoint replay watermark {state.last_event_id!r} is missing "
                f"for manifest {state.manifest_id!r}"
            )
            raise CheckpointConflictError(self._composite_name, detail) from error

        if not replay_entries:
            self._emit_checkpoint_load_status("replay_not_needed")
            return state

        replay_projection: RunLedgerReplayProjection = project_run_ledger_replay(
            replay_entries
        )
        try:
            ensure_projection_coverage(
                composite_name=self._composite_name,
                state=state,
                replay_projection=replay_projection,
                logger=self._logger,
            )
        except CheckpointConflictError:
            self._emit_checkpoint_load_status("replay_conflict")
            raise
        # Explicit constructor path via merge_replay_projection_state keeps
        # the type as CompositeCheckpointState (not DataclassInstance/replace).
        replayed_state: CompositeCheckpointState = merge_replay_projection_state(
            state=state,
            replay_projection=replay_projection,
        )
        log_rich_checkpoint_projection(
            logger=self._logger,
            composite_name=self._composite_name,
            state=state,
            replayed_state=replayed_state,
            replay_projection=replay_projection,
        )
        self._emit_checkpoint_load_status("replayed")
        return replayed_state
