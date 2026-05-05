"""Completion/finalization helpers for composite runner orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runner_pkg.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_helpers import (
    calculate_had_warnings,
)
from bioetl.application.composite.runner_pkg.runner_result_types import (
    CompositeResultBuildContext,
    CompositeResultBuildRequest,
    _PreparedCompositeResultContext,
)
from bioetl.application.runtime_timestamps import derive_completion_timestamp
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint import (
        CompositeCheckpointService,
        CompositeCheckpointState,
    )
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "CompositePipelineFinalizationContext",
    "CompositePipelineFinalizationRequest",
    "CompositePipelineFinalizationResult",
    "CompositeResultBuildContext",
    "CompositeResultBuildRequest",
    "build_composite_result",
    "finalize_composite_result",
    "finalize_pipeline",
    "log_composite_completion",
    "prepare_composite_result_context",
]


class _CompositePipelineFinalizationHostProtocol(Protocol):
    _checkpoint_manager: CompositeCheckpointService

    def _transition_to_completed_state(
        self,
        state: CompositeCheckpointState,
    ) -> CompositeCheckpointState: ...

    async def _persist_completed_state(
        self,
        state: CompositeCheckpointState,
    ) -> None: ...

    async def _delete_checkpoint_safe(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CompositePipelineFinalizationContext:
    """Normalized context for terminal checkpoint finalization."""

    state: CompositeCheckpointState


@dataclass(frozen=True, slots=True)
class CompositePipelineFinalizationResult:
    """Terminal checkpoint state produced by finalization helpers."""

    completed_state: CompositeCheckpointState


def prepare_composite_result_context(
    *,
    request: CompositeResultBuildContext,
    logger: LoggerPort,
) -> _PreparedCompositeResultContext:
    """Resolve completion metadata before final CompositeResult assembly."""
    completed_at = _resolve_completed_at(request)
    started = request.started_at or completed_at
    had_warnings = calculate_had_warnings(
        request.artifacts.enrichment_results,
        request.required_enrichers,
        request.composite_name,
        logger,
    )
    return _PreparedCompositeResultContext(
        artifacts=request.artifacts,
        completed_at=completed_at,
        total_duration=(completed_at - started).total_seconds(),
        had_warnings=had_warnings,
    )


def log_composite_completion(
    *,
    request: CompositeResultBuildContext,
    context: _PreparedCompositeResultContext,
    observer: CompositeLifecycleObserverService,
) -> None:
    """Emit the canonical completion event for composite runs."""
    observer.emit_run_completed(
        composite_name=request.composite_name,
        run_id=request.run_id,
        duration_seconds=context.total_duration,
        had_warnings=context.had_warnings,
    )


def _resolve_completed_at(request: CompositeResultBuildContext) -> datetime:
    """Derive deterministic completion timestamp from captured start context."""
    if request.started_at is None or request.start_time is None:
        raise RuntimeError(
            "Composite result timestamp requires captured start context. "
            "CompositePipelineRunner must set wall and monotonic start times before completion."
        )
    completed_at, _ = derive_completion_timestamp(
        started_at=request.started_at,
        started_monotonic=request.start_time,
        completed_monotonic=time.monotonic(),
    )
    return completed_at


def finalize_composite_result(
    *,
    request: CompositeResultBuildContext,
    context: _PreparedCompositeResultContext,
) -> CompositeResult:
    """Assemble the final CompositeResult from the prepared completion context."""
    artifacts = context.artifacts
    return CompositeResult(
        composite_name=request.composite_name,
        composite_run_id=request.run_id,
        seed_result=artifacts.seed_result,
        dependency_results=artifacts.dependency_results,
        enrichment_results=artifacts.enrichment_results,
        merge_result=artifacts.merge_result,
        total_duration_seconds=context.total_duration,
        started_at=request.started_at,
        completed_at=context.completed_at,
        had_warnings=context.had_warnings,
        original_run_id=request.original_run_id,
        _required_enrichers=request.required_enrichers,
        _required_dependencies=request.required_dependencies,
    )


def build_composite_result(
    *,
    request: CompositeResultBuildContext,
    logger: LoggerPort,
    observer: CompositeLifecycleObserverService,
) -> CompositeResult:
    """Prepare, log, and assemble the final composite result in one seam."""
    context = prepare_composite_result_context(request=request, logger=logger)
    log_composite_completion(request=request, context=context, observer=observer)
    return finalize_composite_result(request=request, context=context)


async def finalize_pipeline(
    host: _CompositePipelineFinalizationHostProtocol,
    request: CompositePipelineFinalizationContext,
) -> CompositePipelineFinalizationResult:
    """Finalize checkpoint state, cleanup resume state, and purge orphans."""
    completed_state = host._transition_to_completed_state(request.state)
    await host._persist_completed_state(completed_state)
    await host._delete_checkpoint_safe()
    try:
        await host._checkpoint_manager.delete_orphaned()
    except (*CHECKPOINT_NON_FATAL_ERRORS, BioETLError):
        pass
    return CompositePipelineFinalizationResult(completed_state=completed_state)


CompositePipelineFinalizationRequest = CompositePipelineFinalizationContext
