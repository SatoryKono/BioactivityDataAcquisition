"""Compose infrastructure probes and resolved Medallion startup validation."""

from __future__ import annotations
from typing import TYPE_CHECKING
from bioetl.application.core.preflight import (
    HealthAggregator,
    MedallionConfigValidator,
    PreflightService,
)
from bioetl.composition.factories.pipeline._preflight_health_monitor import (
    build_preflight_health_monitor,
)
from bioetl.composition.factories.storage._context_resolution import (
    build_preflight_layer_config,
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
        layer_config=build_preflight_layer_config(
            pipeline.services.storage, context.yaml_config
        ),
    )
