"""Lock-held execution ordering helpers for composite runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.application.composite.runner_pkg.runner_models import (
    CompositeExecutionContext,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import CompositeCheckpointState
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
        MergeResult,
        SeedResult,
    )

__all__ = [
    "CompositeLockedExecutionContext",
    "CompositeLockedExecutionResult",
    "execute_locked_run_phases",
]


def _record_enrichment_stage_completed_if_supported(
    host: object,
    enrichment_results: dict[str, EnrichmentResult],
) -> None:
    """Record optional enrichment ledger event when host exposes callback."""
    record = getattr(host, "_record_enrichment_stage_completed", None)
    if callable(record):
        record(enrichment_results)


class _CompositeLockedExecutionHostProtocol(Protocol):
    async def _execute_seed_phase(
        self,
        state: CompositeCheckpointState,
    ) -> tuple[CompositeCheckpointState, SeedResult]: ...

    async def _extract_enrichment_keys(self) -> pl.DataFrame: ...

    async def _execute_dependencies_phase(
        self,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, DependencyResult]]: ...

    async def _execute_enrichment_phase(
        self,
        state: CompositeCheckpointState,
        keys_df: pl.DataFrame,
    ) -> tuple[CompositeCheckpointState, dict[str, EnrichmentResult]]: ...

    async def _transition_to_enrichment_completed(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState: ...

    def _record_enrichment_stage_completed(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None: ...

    async def _execute_merge_stage(
        self,
        state: CompositeCheckpointState,
        enrichment_results: dict[str, EnrichmentResult],
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> tuple[CompositeCheckpointState, MergeResult | None]: ...


@dataclass(frozen=True, slots=True)
class CompositeLockedExecutionContext:
    """Normalized state handoff into lock-held phase execution."""

    state: CompositeCheckpointState


@dataclass(frozen=True, slots=True)
class CompositeLockedExecutionResult:
    """Resolved stage outputs and post-phase checkpoint state."""

    state: CompositeCheckpointState
    execution_context: CompositeExecutionContext


async def execute_locked_run_phases(
    host: _CompositeLockedExecutionHostProtocol,
    request: CompositeLockedExecutionContext,
) -> CompositeLockedExecutionResult:
    """Execute composite phases in the canonical lock-held order."""
    state, seed_result = await host._execute_seed_phase(request.state)
    keys_df = await host._extract_enrichment_keys()
    state, dependency_results = await host._execute_dependencies_phase(state, keys_df)
    state, enrichment_results = await host._execute_enrichment_phase(state, keys_df)
    state = await host._transition_to_enrichment_completed(state)
    _record_enrichment_stage_completed_if_supported(host, enrichment_results)
    state, merge_result = await host._execute_merge_stage(
        state,
        enrichment_results,
        dependency_results,
    )
    return CompositeLockedExecutionResult(
        state=state,
        execution_context=CompositeExecutionContext(
            seed_result=seed_result,
            dependency_results=dependency_results,
            enrichment_results=enrichment_results,
            merge_result=merge_result,
        ),
    )


CompositeLockedExecutionRequest = CompositeLockedExecutionContext
