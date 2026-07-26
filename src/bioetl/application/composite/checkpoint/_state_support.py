"""Support helpers for composite checkpoint state transitions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, TypeVar

from bioetl.application.runtime_clock import resolve_runtime_clock
from bioetl.domain.composite.state import CompositePipelineState

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
        SeedResult,
    )
    from bioetl.domain.ports import ClockPort
    from bioetl.domain.types import JsonDict

T = TypeVar("T")
TCheckpointState = TypeVar("TCheckpointState", bound="CompositeCheckpointState")


def _current_utc_now(clock: ClockPort | None = None) -> datetime:
    """Return current UTC timestamp from the required ClockPort seam."""
    return resolve_runtime_clock(clock).now()


def with_seed_completed(
    checkpoint_state: CompositeCheckpointState,
    result: SeedResult,
    *,
    clock: ClockPort | None = None,
) -> CompositeCheckpointState:
    """Return a copy with completed seed metadata."""
    return _replace_checkpoint_state(
        checkpoint_state,
        state=CompositePipelineState.SEED_COMPLETED,
        seed_completed=True,
        seed_result=result,
        clock=clock,
    )


def with_dependency_completed(
    checkpoint_state: CompositeCheckpointState,
    dependency_name: str,
    result: DependencyResult,
    *,
    clock: ClockPort | None = None,
) -> CompositeCheckpointState:
    """Return a copy with a completed dependency."""
    return _replace_checkpoint_state(
        checkpoint_state,
        state=CompositePipelineState.DEPENDENCIES_RUNNING,
        completed_dependencies=frozenset(
            {*checkpoint_state.completed_dependencies, dependency_name}
        ),
        dependency_results={
            **checkpoint_state.dependency_results,
            dependency_name: result,
        },
        clock=clock,
    )


def with_enricher_completed(
    checkpoint_state: CompositeCheckpointState,
    enricher_name: str,
    result: EnrichmentResult,
    *,
    clock: ClockPort | None = None,
) -> CompositeCheckpointState:
    """Return a copy with a completed enricher."""
    return _replace_checkpoint_state(
        checkpoint_state,
        state=CompositePipelineState.ENRICHING,
        completed_enrichers=frozenset(
            {*checkpoint_state.completed_enrichers, enricher_name}
        ),
        enrichment_results={
            **checkpoint_state.enrichment_results,
            enricher_name: result,
        },
        clock=clock,
    )


def with_state(
    checkpoint_state: CompositeCheckpointState,
    new_state: CompositePipelineState,
    *,
    clock: ClockPort | None = None,
) -> CompositeCheckpointState:
    """Return a copy with an updated FSM state."""
    return _replace_checkpoint_state(checkpoint_state, state=new_state, clock=clock)


def with_merge_completed(
    checkpoint_state: CompositeCheckpointState,
    result: JsonDict,
    *,
    clock: ClockPort | None = None,
) -> CompositeCheckpointState:
    """Return a copy with completed merge metadata."""
    return _replace_checkpoint_state(
        checkpoint_state,
        state=CompositePipelineState.MERGING,
        merge_completed=True,
        merge_result=result,
        clock=clock,
    )


def is_resumable(checkpoint_state: CompositeCheckpointState) -> bool:
    """Check if this checkpoint can be resumed."""
    return (
        checkpoint_state.state.is_resumable
        or checkpoint_state.seed_completed
        or bool(checkpoint_state.completed_enrichers)
    )


def _replace_checkpoint_state[TCheckpointState: "CompositeCheckpointState"](
    checkpoint_state: TCheckpointState,
    *,
    clock: ClockPort | None = None,
    updated_at: datetime | None = None,
    state: CompositePipelineState | None = None,
    seed_completed: bool | None = None,
    seed_result: SeedResult | None = None,
    completed_dependencies: frozenset[str] | None = None,
    dependency_results: dict[str, DependencyResult] | None = None,
    completed_enrichers: frozenset[str] | None = None,
    enrichment_results: dict[str, EnrichmentResult] | None = None,
    merge_completed: bool | None = None,
    merge_result: JsonDict | None = None,
) -> TCheckpointState:
    def _resolved(current: T, override: T | None) -> T:
        return current if override is None else override

    checkpoint_state_type = type(checkpoint_state)
    checkpoint_state_copy = checkpoint_state_type(
        composite_name=checkpoint_state.composite_name,
        run_id=checkpoint_state.run_id,
        state=_resolved(checkpoint_state.state, state),
        seed_completed=_resolved(checkpoint_state.seed_completed, seed_completed),
        seed_result=_resolved(checkpoint_state.seed_result, seed_result),
        completed_dependencies=_resolved(
            checkpoint_state.completed_dependencies,
            completed_dependencies,
        ),
        dependency_results=_resolved(
            checkpoint_state.dependency_results,
            dependency_results,
        ),
        completed_enrichers=_resolved(
            checkpoint_state.completed_enrichers,
            completed_enrichers,
        ),
        enrichment_results=_resolved(
            checkpoint_state.enrichment_results,
            enrichment_results,
        ),
        merge_completed=_resolved(checkpoint_state.merge_completed, merge_completed),
        merge_result=_resolved(checkpoint_state.merge_result, merge_result),
        checkpoint_schema_version=checkpoint_state.checkpoint_schema_version,
        effective_config_hash=checkpoint_state.effective_config_hash,
        effective_config_artifact_id=checkpoint_state.effective_config_artifact_id,
        execution_fingerprint=checkpoint_state.execution_fingerprint,
        dq_contract_compatibility_hash=(
            checkpoint_state.dq_contract_compatibility_hash
        ),
        input_snapshot_fingerprint=checkpoint_state.input_snapshot_fingerprint,
        contract_ref=checkpoint_state.contract_ref,
        contract_version=checkpoint_state.contract_version,
        manifest_id=checkpoint_state.manifest_id,
        composite_run_identity=checkpoint_state.composite_run_identity,
        last_event_id=checkpoint_state.last_event_id,
        last_event_occurred_at=checkpoint_state.last_event_occurred_at,
        created_at=checkpoint_state.created_at,
        updated_at=updated_at or _current_utc_now(clock),
    )
    return checkpoint_state_copy
