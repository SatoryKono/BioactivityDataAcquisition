"""Preflight and observer builders for pipeline runner assembly."""

from __future__ import annotations

from typing import TYPE_CHECKING
from bioetl.composition.factories.services._preflight import (
    build_preflight_service as _build_preflight_service,
)

from bioetl.application.observability.observer import (
    PipelineObserver,
    PipelineObserverParams,
)
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.application.core.preflight import PreflightService
    from bioetl.composition.factories.pipeline._runner_assembly_support import (
        RunnerAssemblyContext,
    )


def build_preflight_service(context: RunnerAssemblyContext) -> PreflightService:
    """Delegate startup service construction to the service factory owner."""
    return _build_preflight_service(context)


def build_observer(context: RunnerAssemblyContext) -> PipelineObserver:
    """Build the pipeline observer bound to the current run context."""
    pipeline = context.pipeline
    pipeline_context = pipeline.context
    return PipelineObserver(
        identity=PipelineObserverParams(
            pipeline_name=pipeline.config.pipeline_name,
            run_id=pipeline_context.run_id,
            run_type=pipeline.runtime.run_type,
            manifest_id=getattr(pipeline_context, "manifest_id", None),
            entity=getattr(pipeline_context, "entity", None),
            effective_config_hash=getattr(
                pipeline_context, "effective_config_hash", None
            ),
            contract_ref=getattr(pipeline_context, "contract_ref", None),
            contract_version=getattr(pipeline_context, "contract_version", None),
            composite_run_id=getattr(pipeline_context, "composite_run_id", None),
        ),
        metrics=pipeline.services.metrics,
        logger=context.logger_port,
        clock=SystemClock(),
        tracer=context.observability.tracer,
    )
