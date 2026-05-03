# mypy: disable-error-code="attr-defined"
"""Runner construction helpers for pipeline factory assembly."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.core.wiring.factory import (
    BasePipeline,
    BatchExecutor,
    CheckpointRuntimeService,
    LockRuntimeService,
    PipelineRunner,
    PipelineRunnerDependencies,
    PostrunService,
    PreflightService,
)
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.factories.services.common_service_wiring import resolve_tracer
from bioetl.composition.observability import ObservabilityBundle


@dataclass(frozen=True, slots=True)
class RunnerAssemblyParts:
    """Concrete runner collaborators assembled before PipelineRunner creation."""

    checkpoint_manager: CheckpointRuntimeService
    lifecycle_service: MedallionLifecycleService
    lock_runtime_service: LockRuntimeService
    preflight_service: PreflightService
    postrun_service: PostrunService
    observer: PipelineObserver
    batch_executor: BatchExecutor


@dataclass(frozen=True, slots=True)
class RunnerConstructorPayload:
    """Typed payload passed from assembly seams into final runner construction."""

    pipeline: BasePipeline
    observability: ObservabilityBundle
    parts: RunnerAssemblyParts


def create_pipeline_runner(
    *,
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    executor: BatchExecutor,
    checkpoint_manager: CheckpointRuntimeService,
    lock_runtime_service: LockRuntimeService,
    preflight_service: PreflightService,
    postrun_service: PostrunService,
    lifecycle_service: MedallionLifecycleService,
    observer: PipelineObserver,
) -> PipelineRunner:
    """Build the fully wired runtime PipelineRunner instance."""
    resolved_tracer = resolve_tracer(observability.tracer)
    dependencies = PipelineRunnerDependencies(
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        lock_runtime_service=lock_runtime_service,
        preflight=preflight_service,
        postrun=postrun_service,
        lifecycle_service=lifecycle_service,
        observer=observer,
        shutdown_signal=pipeline.shutdown_signal,
    )
    return PipelineRunner(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        dependencies=dependencies,
        pipeline=pipeline,
        tracer=resolved_tracer,
    )


def create_pipeline_runner_from_payload(
    payload: RunnerConstructorPayload,
) -> PipelineRunner:
    """Build a PipelineRunner from a pre-assembled constructor payload."""
    return create_pipeline_runner(
        pipeline=payload.pipeline,
        observability=payload.observability,
        executor=payload.parts.batch_executor,
        checkpoint_manager=payload.parts.checkpoint_manager,
        lock_runtime_service=payload.parts.lock_runtime_service,
        preflight_service=payload.parts.preflight_service,
        postrun_service=payload.parts.postrun_service,
        lifecycle_service=payload.parts.lifecycle_service,
        observer=payload.parts.observer,
    )
