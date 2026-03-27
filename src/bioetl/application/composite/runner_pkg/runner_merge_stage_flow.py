"""Reusable merge-stage helpers for composite runner orchestration."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_constants import (
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_helpers import (
    get_mergeable_dependencies,
    get_mergeable_enrichers,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_runtime import (
    handle_dry_run_merge_skip,
    handle_merge_phase_exception,
    handle_merge_success,
    start_merge_phase,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_types import (
    _CompositeRunnerMergeStageHostProtocol,
    _PreparedMergeInputs,
    _PreparedMergeRequest,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)
from bioetl.domain.exceptions import BioETLError

__all__ = [
    "build_merge_inputs",
    "build_merge_request",
    "execute_merge_stage",
    "execute_started_merge_phase",
    "run_prepared_merge_request",
]


def build_merge_inputs(
    host: _CompositeRunnerMergeStageHostProtocol,
    enrichment_results: dict[str, EnrichmentResult],
    dependency_results: dict[str, DependencyResult] | None,
) -> _PreparedMergeInputs:
    """Build mergeable enrichers and dependencies for the merge stage."""
    mergeable_enrichers = get_mergeable_enrichers(
        enrichment_results,
        host._config.enrichers,
        host._logger,
    )
    mergeable_dependencies = get_mergeable_dependencies(
        dependency_results or {},
        host._config.dependencies,
        host._logger,
    )
    return _PreparedMergeInputs(
        enrichers=mergeable_enrichers,
        dependencies=mergeable_dependencies,
    )


def build_merge_request(
    host: _CompositeRunnerMergeStageHostProtocol,
    enrichment_results: dict[str, EnrichmentResult],
    dependency_results: dict[str, DependencyResult] | None,
) -> _PreparedMergeRequest:
    """Build the canonical merge request for the merger seam."""
    prepared_inputs = build_merge_inputs(
        host,
        enrichment_results,
        dependency_results,
    )
    return _PreparedMergeRequest(
        seed_table=host._config.seed.silver_table,
        seed_pipeline=host._config.seed.pipeline,
        enrichers=prepared_inputs.enrichers,
        enrichment_results=enrichment_results,
        run_id=host._run_id_str,
        dependencies=prepared_inputs.dependencies,
        dependency_results=dependency_results,
    )


async def run_prepared_merge_request(
    host: _CompositeRunnerMergeStageHostProtocol,
    request: _PreparedMergeRequest,
) -> MergeResult:
    """Run merger through a normalized request context."""
    return await host._merger.merge(
        seed_table=request.seed_table,
        enrichers=request.enrichers,
        enrichment_results=request.enrichment_results,
        run_id=request.run_id,
        seed_pipeline=request.seed_pipeline,
        dependencies=request.dependencies,
        dependency_results=request.dependency_results,
    )


async def execute_started_merge_phase(
    host: _CompositeRunnerMergeStageHostProtocol,
    state: CompositeCheckpointState,
    *,
    enrichment_results: dict[str, EnrichmentResult],
    dependency_results: dict[str, DependencyResult] | None,
) -> MergeResult:
    """Run merge after the phase has been started and handle success/errors."""
    try:
        prepared_request = build_merge_request(
            host,
            enrichment_results,
            dependency_results,
        )
        merge_result = await run_prepared_merge_request(host, prepared_request)
        await handle_merge_success(host, merge_result)
    except (*PIPELINE_EXECUTION_ERRORS, BioETLError) as merge_error:
        await handle_merge_phase_exception(host, state, merge_error)
        raise
    return merge_result


async def execute_merge_stage(
    host: _CompositeRunnerMergeStageHostProtocol,
    state: CompositeCheckpointState,
    enrichment_results: dict[str, EnrichmentResult],
    dependency_results: dict[str, DependencyResult] | None = None,
) -> tuple[CompositeCheckpointState, MergeResult | None]:
    """Execute merge stage or skip it in dry-run mode."""
    merge_result: MergeResult | None = None

    if not host._runtime.dry_run:
        state = await start_merge_phase(host, state)
        merge_result = await execute_started_merge_phase(
            host,
            state,
            enrichment_results=enrichment_results,
            dependency_results=dependency_results,
        )
    else:
        state = handle_dry_run_merge_skip(host, state)

    return state, merge_result
