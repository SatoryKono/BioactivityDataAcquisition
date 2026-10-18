"""Lock-held execution ordering helpers for composite runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.application.composite.runtime_models import (
    CompositeExecutionContext,
)
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.exceptions import CheckpointConflictError

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
    "CompositeRunPhaseService",
    "execute_locked_run_phases",
]


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


@dataclass(frozen=True, slots=True)
class _CompositePreMergeExecutionResult:
    """Resolved pre-merge phase outputs and checkpoint state."""

    state: CompositeCheckpointState
    seed_result: SeedResult
    dependency_results: dict[str, DependencyResult]
    enrichment_results: dict[str, EnrichmentResult]


def _build_execution_context(
    *,
    seed_result: SeedResult,
    dependency_results: dict[str, DependencyResult],
    enrichment_results: dict[str, EnrichmentResult],
    merge_result: MergeResult | None,
) -> CompositeExecutionContext:
    """Assemble the final composite execution context from phase outputs."""
    return CompositeExecutionContext(
        seed_result=seed_result,
        dependency_results=dependency_results,
        enrichment_results=enrichment_results,
        merge_result=merge_result,
    )


def _legacy_completed_execution_result(
    state: CompositeCheckpointState,
) -> CompositeLockedExecutionResult:
    """Resume only finalization for a checkpoint written after legacy CV.

    The legacy state is emitted after merge and cross-validation. Re-running
    the current combined merge/CV stage would repeat completed writes. The
    migration marker instead requires enough persisted merge evidence to build
    the terminal result; if it is missing, fail closed without replaying work.
    """
    if not state.seed_completed or state.seed_result is None:
        raise CheckpointConflictError(
            state.composite_name,
            "legacy cross_validation_completed checkpoint lacks completed seed result",
        )
    payload = state.merge_result
    if not isinstance(payload, dict) or not isinstance(
        payload.get("records_merged"), int
    ):
        raise CheckpointConflictError(
            state.composite_name,
            "legacy cross_validation_completed checkpoint lacks merge result evidence",
        )

    merge_fields = {
        "records_merged",
        "records_from_seed",
        "records_enriched",
        "records_fully_enriched",
        "sources_used",
        "field_coverage",
        "duration_seconds",
        "output_silver_path",
        "output_gold_path",
        "lineage_summary",
        "quarantine_payloads",
    }
    merge_result = MergeResult(
        **{key: value for key, value in payload.items() if key in merge_fields}
    )
    execution_context = _build_execution_context(
        seed_result=state.seed_result,
        dependency_results=state.dependency_results,
        enrichment_results=state.enrichment_results,
        merge_result=merge_result,
    )
    return CompositeLockedExecutionResult(
        state=state,
        execution_context=execution_context,
    )


async def _complete_enrichment_phase(
    host: _CompositeLockedExecutionHostProtocol,
    state: CompositeCheckpointState,
    enrichment_results: dict[str, EnrichmentResult],
) -> CompositeCheckpointState:
    """Apply the canonical enrichment-completed transition and hook."""
    completed_state = await host._transition_to_enrichment_completed(state)
    host._record_enrichment_stage_completed(enrichment_results)
    return completed_state


async def _run_pre_merge_phases(
    host: _CompositeLockedExecutionHostProtocol,
    request: CompositeLockedExecutionContext,
) -> _CompositePreMergeExecutionResult:
    """Execute canonical seed/dependency/enrichment phases before merge."""
    state, seed_result = await host._execute_seed_phase(request.state)
    keys_df = await host._extract_enrichment_keys()
    state, dependency_results = await host._execute_dependencies_phase(state, keys_df)
    state, enrichment_results = await host._execute_enrichment_phase(state, keys_df)
    state = await _complete_enrichment_phase(host, state, enrichment_results)
    return _CompositePreMergeExecutionResult(
        state=state,
        seed_result=seed_result,
        dependency_results=dependency_results,
        enrichment_results=enrichment_results,
    )


async def _run_merge_phase(
    host: _CompositeLockedExecutionHostProtocol,
    pre_merge_result: _CompositePreMergeExecutionResult,
) -> tuple[CompositeCheckpointState, MergeResult | None]:
    """Execute canonical merge handoff from pre-merge phase outputs."""
    return await host._execute_merge_stage(
        pre_merge_result.state,
        pre_merge_result.enrichment_results,
        pre_merge_result.dependency_results,
    )


@dataclass(frozen=True, slots=True)
class CompositeRunPhaseService:
    """Application service that owns lock-held composite phase ordering."""

    async def execute_pre_merge(
        self,
        host: _CompositeLockedExecutionHostProtocol,
        request: CompositeLockedExecutionContext,
    ) -> _CompositePreMergeExecutionResult:
        """Execute seed, dependency, and enrichment phases before merge."""
        return await _run_pre_merge_phases(host, request)

    async def execute_merge(
        self,
        host: _CompositeLockedExecutionHostProtocol,
        pre_merge_result: _CompositePreMergeExecutionResult,
    ) -> tuple[CompositeCheckpointState, MergeResult | None]:
        """Execute the merge phase from explicit pre-merge outputs."""
        return await _run_merge_phase(host, pre_merge_result)

    async def execute(
        self,
        host: _CompositeLockedExecutionHostProtocol,
        request: CompositeLockedExecutionContext,
    ) -> CompositeLockedExecutionResult:
        """Execute composite phases in the canonical lock-held order."""
        if getattr(request.state, "legacy_cv_resume_blocked", False) is True:
            raise CheckpointConflictError(
                request.state.composite_name,
                "legacy cross_validation_running checkpoint cannot resume safely: "
                "the current merge service combines merge writes and cross-validation, "
                "so replaying it would repeat completed merge writes",
            )
        if getattr(request.state, "legacy_cv_completion_pending", False) is True:
            return _legacy_completed_execution_result(request.state)
        pre_merge_result = await self.execute_pre_merge(host, request)
        state, merge_result = await self.execute_merge(host, pre_merge_result)
        return CompositeLockedExecutionResult(
            state=state,
            execution_context=_build_execution_context(
                seed_result=pre_merge_result.seed_result,
                dependency_results=pre_merge_result.dependency_results,
                enrichment_results=pre_merge_result.enrichment_results,
                merge_result=merge_result,
            ),
        )


async def execute_locked_run_phases(
    host: _CompositeLockedExecutionHostProtocol,
    request: CompositeLockedExecutionContext,
) -> CompositeLockedExecutionResult:
    """Execute composite phases in the canonical lock-held order."""
    return await CompositeRunPhaseService().execute(host, request)


CompositeLockedExecutionRequest = CompositeLockedExecutionContext
