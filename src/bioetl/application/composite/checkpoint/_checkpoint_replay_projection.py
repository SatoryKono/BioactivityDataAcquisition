"""Replay-projection helpers for composite checkpoint load orchestration."""

from __future__ import annotations

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.control_plane.run_ledger import RunLedgerReplayProjection
from bioetl.domain.exceptions import CheckpointConflictError
from bioetl.domain.ports import LoggerPort

__all__ = [
    "ensure_projection_coverage",
    "log_rich_checkpoint_projection",
    "merge_replay_projection_state",
]


def merge_replay_projection_state(
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


def log_rich_checkpoint_projection(
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


def ensure_projection_coverage(
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
