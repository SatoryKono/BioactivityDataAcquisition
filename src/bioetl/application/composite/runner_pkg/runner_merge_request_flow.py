"""Merge request preparation and merger dispatch helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, cast

from bioetl.application.composite.merger_orchestration import (
    MergeExecutionRequest,
    build_merge_execution_request,
    resolve_merge_metadata_timestamp,
)
from bioetl.application.composite.runner_pkg.runner_constants import (
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_helpers import (
    get_mergeable_dependencies,
    get_mergeable_enrichers,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_runtime import (
    handle_merge_phase_exception,
    handle_merge_success,
)
from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_merge_stage_types import (
    _CompositeRunnerMergeStageHostProtocol,
    _PreparedMergeInputs,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)
from bioetl.domain.exceptions import BioETLError


class _MergerProtocol(Protocol):
    """Structural interface for merger instances and test doubles."""

    __dict__: dict[str, object]


__all__ = [
    "build_merge_inputs",
    "execute_started_merge_phase",
    "get_explicit_merger_method",
    "prepare_merge_request",
    "run_prepared_merge_request",
]


def get_explicit_merger_method(
    merger: _MergerProtocol,
    method_name: str,
) -> Callable[..., Awaitable[MergeResult]] | None:
    """Ignore autovivified mock attrs; accept real or explicitly assigned methods."""
    instance_attrs = vars(merger)
    if method_name in instance_attrs:
        method = instance_attrs[method_name]
        if not callable(method):
            return None
        return cast(Callable[..., Awaitable[MergeResult]], method)
    method = getattr(type(merger), method_name, None)
    if not callable(method):
        return None
    return cast(
        Callable[..., Awaitable[MergeResult]],
        method.__get__(merger, type(merger)),
    )


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


def prepare_merge_request(
    host: _CompositeRunnerMergeStageHostProtocol,
    enrichment_results: dict[str, EnrichmentResult],
    dependency_results: dict[str, DependencyResult] | None,
) -> MergeExecutionRequest:
    """Build the canonical merge request for the merger seam."""
    prepared_inputs = build_merge_inputs(
        host,
        enrichment_results,
        dependency_results,
    )
    return build_merge_execution_request(
        seed_table=host._config.seed.silver_table,
        seed_pipeline=host._config.seed.pipeline,
        enrichers=prepared_inputs.enrichers,
        enrichment_results=enrichment_results,
        run_id=host._run_id_str,
        metadata_timestamp=resolve_merge_metadata_timestamp(
            getattr(host._runtime, "cached_bronze_date", None)
        ),
        dependencies=prepared_inputs.dependencies,
        dependency_results=dependency_results,
    )


async def run_prepared_merge_request(
    host: _CompositeRunnerMergeStageHostProtocol,
    request: MergeExecutionRequest,
) -> MergeResult:
    """Run merger through a normalized request context."""
    merger = host._merger
    execute_request = get_explicit_merger_method(merger, "execute_request")
    if execute_request is not None:
        return await execute_request(request)
    merge = get_explicit_merger_method(merger, "merge")
    if merge is None:
        raise AttributeError(
            "Merger does not implement execute_request() or merge()"
        )
    return await merge(
        request.seed_table,
        request.enrichers,
        request.enrichment_results,
        request.run_id,
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
        prepared_request = prepare_merge_request(
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
