"""Loading workflow for composite checkpoint state."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

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
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.composite.port_types import (
    ClockPort,
    CompositeCheckpointPort,
    LoggerPort,
    MetricsPort,
    RunLedgerPort,
)
from bioetl.domain.control_plane.run_ledger import project_run_ledger_replay
from bioetl.domain.exceptions import CheckpointConflictError


def _replace_checkpoint_state(
    state: CompositeCheckpointState, /, **changes: object
) -> CompositeCheckpointState:
    """Return a checkpoint state with the requested field updates applied."""
    return cast(CompositeCheckpointState, replace(state, **changes))


def _contract_ref_mismatch(
    *,
    state: CompositeCheckpointState,
    expected_contract_ref: str,
    logger: LoggerPort,
    composite_name: str,
) -> str | None:
    del logger, composite_name
    if not expected_contract_ref:
        return None
    if state.contract_ref:
        if state.contract_ref != expected_contract_ref:
            return f"contract_ref {state.contract_ref!r} != {expected_contract_ref!r}"
        return None

    return "checkpoint missing contract_ref anchor"


def _contract_version_mismatch(
    *,
    state: CompositeCheckpointState,
    expected_contract_version: str,
    logger: LoggerPort,
    composite_name: str,
) -> str | None:
    del logger, composite_name
    if not expected_contract_version:
        return None
    if state.contract_version:
        if state.contract_version != expected_contract_version:
            return (
                f"contract_version {state.contract_version!r} "
                f"!= {expected_contract_version!r}"
            )
        return None
    return "checkpoint missing contract_version anchor"


def _effective_hash_mismatch(
    *,
    state: CompositeCheckpointState,
    expected_effective_config_hash: str,
    logger: LoggerPort,
    composite_name: str,
) -> str | None:
    del logger, composite_name
    if not expected_effective_config_hash:
        return None
    if state.effective_config_hash:
        if state.effective_config_hash != expected_effective_config_hash:
            return (
                f"effective_config_hash {state.effective_config_hash!r} "
                f"!= {expected_effective_config_hash!r}"
            )
        return None

    return "checkpoint missing effective_config_hash anchor"


def _exact_anchor_mismatch(
    *,
    state_value: str,
    expected_value: str,
    anchor_name: str,
) -> str | None:
    if not expected_value:
        return None
    if not state_value:
        return f"checkpoint missing {anchor_name} anchor"
    if state_value != expected_value:
        return f"{anchor_name} {state_value!r} != {expected_value!r}"
    return None


def _manifest_id_mismatch(
    *,
    state: CompositeCheckpointState,
    expected_manifest_id: str,
    logger: LoggerPort,
    composite_name: str,
) -> str | None:
    del logger, composite_name
    if not expected_manifest_id:
        return None
    if state.manifest_id:
        if state.manifest_id != expected_manifest_id:
            return f"manifest_id {state.manifest_id!r} != {expected_manifest_id!r}"
        return None

    return "checkpoint missing manifest_id anchor"


def _composite_run_identity_mismatch(
    *,
    state: CompositeCheckpointState,
    expected_composite_run_identity: str,
) -> str | None:
    if not expected_composite_run_identity:
        return None
    if not state.composite_run_identity:
        return "checkpoint missing composite_run_identity anchor"
    if state.composite_run_identity != expected_composite_run_identity:
        return (
            "composite_run_identity "
            f"{state.composite_run_identity!r} != {expected_composite_run_identity!r}"
        )
    return None


def validate_resume_compatibility(
    *,
    state: CompositeCheckpointState,
    anchors: ExpectedCheckpointContext,
    logger: LoggerPort,
    composite_name: str,
) -> None:
    """Raise when persisted checkpoint anchors conflict with the current runtime."""
    mismatches = [
        mismatch
        for mismatch in (
            _contract_ref_mismatch(
                state=state,
                expected_contract_ref=anchors.contract_ref,
                logger=logger,
                composite_name=composite_name,
            ),
            _contract_version_mismatch(
                state=state,
                expected_contract_version=anchors.contract_version,
                logger=logger,
                composite_name=composite_name,
            ),
            _effective_hash_mismatch(
                state=state,
                expected_effective_config_hash=anchors.effective_config_hash,
                logger=logger,
                composite_name=composite_name,
            ),
            _exact_anchor_mismatch(
                state_value=state.effective_config_artifact_id,
                expected_value=anchors.effective_config_artifact_id,
                anchor_name="effective_config_artifact_id",
            ),
            _exact_anchor_mismatch(
                state_value=state.execution_fingerprint,
                expected_value=anchors.execution_fingerprint,
                anchor_name="execution_fingerprint",
            ),
            _exact_anchor_mismatch(
                state_value=state.dq_contract_compatibility_hash,
                expected_value=anchors.dq_contract_compatibility_hash,
                anchor_name="dq_contract_compatibility_hash",
            ),
            _manifest_id_mismatch(
                state=state,
                expected_manifest_id=anchors.manifest_id,
                logger=logger,
                composite_name=composite_name,
            ),
            _composite_run_identity_mismatch(
                state=state,
                expected_composite_run_identity=anchors.composite_run_identity,
            ),
        )
        if mismatch is not None
    ]
    if not mismatches:
        return

    detail = "; ".join(mismatches)
    logger.error(
        "Checkpoint incompatible with current runtime anchors",
        composite=composite_name,
        checkpoint_run_id=state.run_id,
        expected_contract_ref=anchors.contract_ref,
        expected_contract_version=anchors.contract_version,
        expected_effective_config_hash=anchors.effective_config_hash,
        expected_effective_config_artifact_id=anchors.effective_config_artifact_id,
        expected_execution_fingerprint=anchors.execution_fingerprint,
        expected_dq_contract_compatibility_hash=(
            anchors.dq_contract_compatibility_hash
        ),
        expected_composite_run_identity=anchors.composite_run_identity,
        checkpoint_contract_ref=state.contract_ref,
        checkpoint_contract_version=state.contract_version,
        checkpoint_effective_config_hash=state.effective_config_hash,
        checkpoint_effective_config_artifact_id=state.effective_config_artifact_id,
        checkpoint_execution_fingerprint=state.execution_fingerprint,
        checkpoint_dq_contract_compatibility_hash=(
            state.dq_contract_compatibility_hash
        ),
        checkpoint_composite_run_identity=state.composite_run_identity,
        reason_code="checkpoint_resume_incompatible",
        incompatibility=detail,
    )
    raise CheckpointConflictError(composite_name, detail)


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
        expected_context: ExpectedCheckpointContext,
        checkpoint_filename: str,
        glob_pattern: str,
        run_ledger_port: RunLedgerPort | None = None,
        metrics: MetricsPort | None = None,
        clock: ClockPort | None = None,
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
        self._clock = clock

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

        state = load_checkpoint_state(
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
        merged_state = merge_expected_anchors(state, self._expected_context)
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
        replayed_state = _replace_checkpoint_state(
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
