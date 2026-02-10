"""Bootstrap function for main pipeline execution.

Contains the primary Composition Root entry point for creating
a fully configured PipelineRunner ready for execution.

This is the main entry point for runtime pipeline execution.
CLI commands should use this via composition/entrypoints.py.
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

__all__ = [
    # Deprecated alias (backward compatibility)
    "bootstrap_pipeline",
    # Canonical name (use this)
    "bootstrap_pipeline_runner",
]


def bootstrap_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
) -> PipelineRunner:
    """Composition Root: Assembles and returns a fully configured PipelineRunner.

    This is the main entry point for creating a pipeline runner. It:
    1. Registers all providers and pipelines (idempotent)
    2. Loads settings and YAML configuration
    3. Bootstraps observability (logging, tracing, metrics)
    4. Builds filter configuration from CLI/YAML
    5. Delegates to the appropriate factory to create the runner

    Layer: Returns application-level runner (PipelineRunner) ready for execution.

    Args:
        ctx: Pipeline run context containing launch parameters including
            pipeline_name, run_id, run_type, resume flag, limit, filters, etc.
        registry: Optional PipelineRegistry instance. If None, uses the
            default global registry. Pass a custom registry for test isolation.

    Returns:
        PipelineRunner: Fully configured runner ready for execution.

    Example:
        >>> from bioetl.domain.context import PipelineRunContext
        >>> from bioetl.domain.types import RunType
        >>> from uuid import uuid4
        >>>
        >>> ctx = PipelineRunContext(
        ...     pipeline_name="chembl_activity",
        ...     run_id=uuid4(),
        ...     run_type=RunType.INCREMENTAL,
        ... )
        >>> runner = bootstrap_pipeline_runner(ctx)
        >>> await runner.run()

        # For test isolation:
        >>> from bioetl.composition.registry import create_registry
        >>> registry = create_registry()
        >>> register_all_pipelines(registry=registry)
        >>> runner = bootstrap_pipeline_runner(ctx, registry=registry)
    """
    # Use provided registry or default
    effective_registry = registry if registry is not None else get_default_registry()

    # Explicit registration (idempotent for default registry)
    register_all_providers()
    register_all_pipelines(registry=registry)

    settings = get_settings()

    # Load validated YAML config first to check for existence
    yaml_config = load_pipeline_config(ctx.pipeline_name)

    # Bootstrap unified observability (includes metrics server start if enabled)
    observability = bootstrap_observability_bundle(
        pipeline=ctx.pipeline_name,
        run_id=ctx.run_id,
        settings=settings,
        log_level=ctx.log_level,
    )

    # Assemble vacuum settings (CLI overrides YAML)
    vacuum = assemble_vacuum_settings(
        cli_vacuum=ctx.vacuum,
        yaml_maintenance=yaml_config.maintenance,
    )

    # Assemble runtime config from resolved parameters
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

    # Assemble filter config (CLI/direct IDs override YAML)
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

    # Assemble cached bronze context
    cached_bronze = assemble_cached_bronze_context(ctx)

    if cached_bronze.enabled:
        observability.logger.info(
            "cached_bronze_mode_enabled",
            bronze_path=cached_bronze.bronze_path,
            bronze_date=cached_bronze.bronze_date,
        )

    # Resolve pipeline factory and delegate runner creation
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


def bootstrap_pipeline(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
) -> PipelineRunner:
    """Composition Root: Assembles and returns a fully configured PipelineRunner.

    .. deprecated::
        Use :func:`bootstrap_pipeline_runner` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        ctx: Pipeline run context containing launch parameters.
        registry: Optional PipelineRegistry instance.

    Returns:
        PipelineRunner: Fully configured runner ready for execution.
    """
    return bootstrap_pipeline_runner(ctx=ctx, registry=registry)
