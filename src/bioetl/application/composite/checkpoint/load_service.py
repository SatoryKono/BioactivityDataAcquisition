"""Loading workflow for composite checkpoint state."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.composite.checkpoint._anchor_context import (
    ExpectedCheckpointContext,
    fresh_checkpoint_state,
    merge_expected_anchors,
)
from bioetl.application.composite.checkpoint._checkpoint_runtime import (
    load_checkpoint_state,
    resolve_resume_checkpoint_filename,
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


def _merge_replay_projection_state(
    *,
    state: CompositeCheckpointState,
    replay_projection: RunLedgerReplayProjection,
) -> CompositeCheckpointState:
    """Apply replay projection fields while preserving snapshot anchors."""
    return CompositeCheckpointState(
        composite_name=state.composite_name,
        run_id=state.run_id,
        state=replay_projection.state or state.state,
        seed_completed=(
            replay_projection.seed_completed
            if replay_projection.seed_completed is not None
            else state.seed_completed
        ),
        seed_result=state.seed_result,
        completed_dependencies=frozenset(
            {*state.completed_dependencies, *replay_projection.completed_dependencies}
        ),
        dependency_results={
            **state.dependency_results,
            **replay_projection.dependency_results,
        },
        completed_enrichers=frozenset(
            {*state.completed_enrichers, *replay_projection.completed_enrichers}
        ),
        enrichment_results={
            **state.enrichment_results,
            **replay_projection.enrichment_results,
        },
        merge_completed=(
            replay_projection.merge_completed
            if replay_projection.merge_completed is not None
            else state.merge_completed
        ),
        merge_result=replay_projection.merge_result or state.merge_result,
        checkpoint_schema_version=state.checkpoint_schema_version,
        effective_config_hash=state.effective_config_hash,
        effective_config_artifact_id=state.effective_config_artifact_id,
        execution_fingerprint=state.execution_fingerprint,
        dq_contract_compatibility_hash=state.dq_contract_compatibility_hash,
        input_snapshot_fingerprint=state.input_snapshot_fingerprint,
        contract_ref=state.contract_ref,
        contract_version=state.contract_version,
        manifest_id=state.manifest_id,
        composite_run_identity=state.composite_run_identity,
        last_event_id=replay_projection.last_event_id,
        last_event_occurred_at=replay_projection.last_event_occurred_at,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


def _log_rich_checkpoint_projection(
    *,
    logger: LoggerPort,
    composite_name: str,
    state: CompositeCheckpointState,
    replayed_state: CompositeCheckpointState,
    replay_projection: RunLedgerReplayProjection,
) -> None:
    """Emit compact replay projection diagnostics."""
    logger.info(
        "Applied rich checkpoint projection from run ledger",
        composite=composite_name,
        manifest_id=state.manifest_id,
        projection_scope="rich_checkpoint_payloads",
        projection_contract="checkpoint_snapshot_plus_ledger_suffix_resume",
        reconstructs=[
            "state",
            "seed_completed",
            "dependency_results",
            "enrichment_results",
            "merge_result",
        ],
        replayed_event_count=replay_projection.replayed_entry_count,
        replayed_dependency_count=len(replay_projection.dependency_results),
        replayed_enricher_count=len(replay_projection.enrichment_results),
        replayed_merge_result=replay_projection.merge_result is not None,
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


def _ensure_projection_coverage(
    *,
    composite_name: str,
    state: CompositeCheckpointState,
    replay_projection: RunLedgerReplayProjection,
    logger: LoggerPort,
) -> None:
    """Fail closed when the bounded replay projector cannot interpret suffix events."""
    if replay_projection.projector_coverage_complete:
        return
    unsupported_entries = [
        {
            "entry_id": entry_id,
            "event_type": event_type,
            "stage": stage,
        }
        for entry_id, event_type, stage in replay_projection.unsupported_replay_entries
    ]
    detail = (
        "checkpoint replay suffix contains unsupported replay-relevant ledger "
        f"entries for projector {replay_projection.projection_contract!r}: "
        f"{unsupported_entries!r}"
    )
    logger.error(
        "Checkpoint replay suffix is outside bounded projector coverage",
        composite=composite_name,
        manifest_id=state.manifest_id,
        checkpoint_run_id=state.run_id,
        projection_contract=replay_projection.projection_contract,
        unsupported_replay_entries=unsupported_entries,
        reason_code="checkpoint_replay_projection_incomplete",
    )
    raise CheckpointConflictError(composite_name, detail)


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
            _ensure_projection_coverage(
                composite_name=self._composite_name,
                state=state,
                replay_projection=replay_projection,
                logger=self._logger,
            )
        except CheckpointConflictError:
            self._emit_checkpoint_load_status("replay_conflict")
            raise
        # Explicit constructor path via _merge_replay_projection_state keeps
        # the type as CompositeCheckpointState (not DataclassInstance/replace).
        replayed_state: CompositeCheckpointState = _merge_replay_projection_state(
            state=state,
            replay_projection=replay_projection,
        )
        _log_rich_checkpoint_projection(
            logger=self._logger,
            composite_name=self._composite_name,
            state=state,
            replayed_state=replayed_state,
            replay_projection=replay_projection,
        )
        self._emit_checkpoint_load_status("replayed")
        return replayed_state
