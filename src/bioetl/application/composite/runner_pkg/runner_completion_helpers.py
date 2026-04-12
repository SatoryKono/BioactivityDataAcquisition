"""Completion/finalization helpers for composite runner orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.application.composite.runner_pkg.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_helpers import (
    calculate_had_warnings,
)
from bioetl.application.composite.runner_pkg.runner_support_types import (
    _PreparedCompositeResultContext,
)
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint import (
        CompositeCheckpointService,
        CompositeCheckpointState,
    )
    from bioetl.application.composite.runtime_models import (
        CompositeExecutionContext,
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


@dataclass(frozen=True, slots=True)
class CompositeResultBuildContext:
    """Explicit data required to assemble the final CompositeResult."""

    artifacts: CompositeExecutionContext
    composite_name: str
    run_id: str
    started_at: datetime | None
    original_run_id: str | None
    required_enrichers: frozenset[str]
    required_dependencies: frozenset[str]


def prepare_composite_result_context(
    *,
    request: CompositeResultBuildContext,
    logger: LoggerPort,
) -> _PreparedCompositeResultContext:
    """Resolve completion metadata before final CompositeResult assembly."""
    completed_at = datetime.now(tz=UTC)
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
    logger: LoggerPort,
) -> None:
    """Emit the canonical completion log payload for composite runs."""
    log_kwargs: dict[str, object] = {
        "composite": request.composite_name,
        "run_id": request.run_id,
        "duration_seconds": context.total_duration,
    }
    if context.had_warnings:
        log_kwargs["status"] = "completed_with_warnings"
        log_kwargs["had_warnings"] = True
    logger.info(PipelineEvent.COMPLETE, **log_kwargs)


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
) -> CompositeResult:
    """Prepare, log, and assemble the final composite result in one seam."""
    context = prepare_composite_result_context(request=request, logger=logger)
    log_composite_completion(request=request, context=context, logger=logger)
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
CompositeResultBuildRequest = CompositeResultBuildContext
