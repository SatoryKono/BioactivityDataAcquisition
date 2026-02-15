"""Leaf builder for runtime pipeline runner construction.

This module contains the concrete assembly logic for creating a configured
PipelineRunner without depending on composition.bootstrap package re-exports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime.assembly import (
    assemble_cached_bronze_context,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
)
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_observability_bundle,
)
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.providers.registration import register_all_providers
from bioetl.composition.registry import PipelineRegistry, get_default_registry
from bioetl.infrastructure.config import get_settings, load_pipeline_config

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import PipelineRunContext


__all__ = ["build_pipeline_runner"]


def build_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
) -> PipelineRunner:
    """Assemble and return a fully configured PipelineRunner."""
    effective_registry = registry if registry is not None else get_default_registry()

    register_all_providers()
    register_all_pipelines(registry=registry)

    settings = get_settings()
    yaml_config = load_pipeline_config(ctx.pipeline_name)

    observability = bootstrap_observability_bundle(
        pipeline=ctx.pipeline_name,
        run_id=ctx.run_id,
        settings=settings,
        log_level=ctx.log_level,
    )

    vacuum = assemble_vacuum_settings(
        cli_vacuum=ctx.vacuum,
        yaml_maintenance=yaml_config.maintenance,
    )

    runtime_config = assemble_runtime_config(
        run_type=ctx.run_type,
        resume=ctx.resume,
        limit=ctx.limit,
        query=ctx.query,
        dry_run=ctx.dry_run,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
        vacuum=vacuum,
        skip_gold=ctx.skip_gold,
    )

    filter_config = assemble_filter_config(
        yaml_filter=yaml_config.input_filter,
        ctx=ctx,
        test_mode=settings.test_mode,
    )

    if filter_config:
        observability.logger.info(
            "input_filter_enabled",
            csv_path=filter_config.source_path,
            column=filter_config.column_name,
            filter_field=filter_config.filter_field,
            source="cli" if ctx.input_filter.enabled else "config",
        )

    cached_bronze = assemble_cached_bronze_context(ctx)

    if cached_bronze.enabled:
        observability.logger.info(
            "cached_bronze_mode_enabled",
            bronze_path=cached_bronze.bronze_path,
            bronze_date=cached_bronze.bronze_date,
        )

    pipeline_def = effective_registry.get(ctx.pipeline_name)
    factory = pipeline_def.factory

    return factory.create_runner(
        run_id=ctx.run_id,
        runtime=runtime_config,
        settings=settings,
        observability=observability,
        filter_config=filter_config,
        config=yaml_config,
        cached_bronze=cached_bronze,
    )
