"""Support helpers for composite checkpoint state transitions."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.context import current_utc_time

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
        SeedResult,
    )
    from bioetl.domain.ports import ClockPort
    from bioetl.domain.types import JsonDict


def _current_utc_now(clock: ClockPort | None = None) -> datetime:
    """Return current UTC timestamp from an injected clock when available."""
    return clock.now() if clock is not None else current_utc_time()


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


def _replace_checkpoint_state(
    checkpoint_state: CompositeCheckpointState,
    *,
    clock: ClockPort | None = None,
    updated_at: datetime | None = None,
    **changes: object,
) -> CompositeCheckpointState:
    # `dataclasses.replace` accepts field-aligned keyword overrides, but mypy
    # cannot infer them from this helper's dynamic kwargs surface.
    return cast(
        "CompositeCheckpointState",
        replace(
            checkpoint_state,
            updated_at=updated_at or _current_utc_now(clock),
            **changes,
        ),
    )
