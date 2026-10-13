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
from bioetl.composition.factories.storage import build_preflight_layer_config
from bioetl.domain.medallion import WriteModePolicy
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.composition.factories.pipeline._runner_assembly_support import (
        RunnerAssemblyContext,
    )


def build_preflight_service(context: RunnerAssemblyContext) -> PreflightService:
    """Build the preflight service for a pipeline runner."""
    pipeline = context.pipeline
    return PreflightService(
        config=pipeline.config,
        context=pipeline.context,
        logger=context.logger_port,
        metrics=pipeline.services.metrics,
        health_aggregator=HealthAggregator(
            logger=context.logger_port,
            health_monitor=build_preflight_health_monitor(pipeline.services.metrics),
            health_check_mode=pipeline.runtime.health_check_mode,
            clock=SystemClock(),
        ),
        medallion_validator=MedallionConfigValidator(
            config=pipeline.config,
            logger=context.logger_port,
            write_mode_policy=WriteModePolicy(),
        ),
        layer_config=build_preflight_layer_config(
            pipeline.services.storage, context.yaml_config
        ),
    )


def build_observer(context: RunnerAssemblyContext) -> PipelineObserver:
    """Build the pipeline observer bound to the current run context."""
    pipeline = context.pipeline
    run_context = pipeline.context
    return PipelineObserver(
        identity=PipelineObserverParams(
            pipeline_name=pipeline.config.pipeline_name,
            run_id=run_context.run_id,
            run_type=pipeline.runtime.run_type,
            manifest_id=getattr(run_context, "manifest_id", None),
            entity=getattr(run_context, "entity", None),
            effective_config_hash=getattr(run_context, "effective_config_hash", None),
            contract_ref=getattr(run_context, "contract_ref", None),
            contract_version=getattr(run_context, "contract_version", None),
            composite_run_id=getattr(run_context, "composite_run_id", None),
        ),
        metrics=pipeline.services.metrics,
        logger=context.logger_port,
        clock=SystemClock(),
        tracer=context.observability.tracer,
    )
