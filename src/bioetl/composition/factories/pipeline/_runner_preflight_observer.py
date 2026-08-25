"""Preflight and observer builders for pipeline runner assembly."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.preflight import (
    HealthAggregator,
    MedallionConfigValidator,
    PreflightService,
)
from bioetl.application.observability.observer import (
    PipelineObserver,
    PipelineObserverParams,
)
from bioetl.composition.factories.pipeline._preflight_health_monitor import (
    build_preflight_health_monitor,
)
from bioetl.domain.medallion import WriteModePolicy
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.composition.factories.pipeline._runner_assembly_support import (
        RunnerAssemblyContext,
    )


def build_preflight_service(context: RunnerAssemblyContext) -> PreflightService:
    """Build the preflight service for a pipeline runner."""
    pipeline = context.pipeline
    health_aggregator = HealthAggregator(
        logger=context.logger_port,
        health_monitor=build_preflight_health_monitor(pipeline.services.metrics),
        health_check_mode=pipeline.runtime.health_check_mode,
        clock=SystemClock(),
    )
    medallion_validator = MedallionConfigValidator(
        config=pipeline.config,
        logger=context.logger_port,
        write_mode_policy=WriteModePolicy(),
    )
    return PreflightService(
        config=pipeline.config,
        context=pipeline.context,
        logger=context.logger_port,
        metrics=pipeline.services.metrics,
        health_aggregator=health_aggregator,
        medallion_validator=medallion_validator,
    )


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
