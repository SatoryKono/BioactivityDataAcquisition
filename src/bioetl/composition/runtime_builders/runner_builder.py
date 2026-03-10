"""Leaf builder facade for runtime pipeline runner construction."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, cast

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers.registration import register_all_providers
from bioetl.composition.registry import PipelineRegistry, get_default_registry
from bioetl.composition.runtime_builders.inputs_resolver import (
    RunnerInputs as _RunnerInputs,
)
from bioetl.composition.runtime_builders.inputs_resolver import (
    VacuumSettings,
    assemble_cached_bronze_context,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
    prepare_runner_inputs,
    resolve_filter_batch_size,
    resolve_health_check_mode,
    validate_pk_contract,
)
from bioetl.composition.runtime_builders.observability_builder import (
    build_observability_bundle,
)
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.ports import NoOpMetrics, NoOpTracing
from bioetl.infrastructure.config import (
    get_settings,
    load_pipeline_config,
    load_source_config,
)
from bioetl.infrastructure.observability import OpenTelemetryTracer, PrometheusMetrics
from bioetl.infrastructure.observability.anomaly import DataQualityMonitor
from bioetl.infrastructure.observability.unified_logger import UnifiedLogger

# Backward-compat alias for legacy imports/tests.
VacuumConfig = VacuumSettings

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import (
        CachedBronzeContext,
        PipelineRunContext,
    )
    from bioetl.domain.context import VacuumSettings as CliVacuumSettings
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import PipelineFactoryPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterConfig as YamlInputFilter,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        MaintenanceConfig,
        PipelineYamlConfig,
    )


__all__ = ["build_pipeline_runner"]


def _assemble_vacuum_settings(
    *,
    cli_vacuum: CliVacuumSettings,
    yaml_maintenance: MaintenanceConfig,
) -> VacuumSettings:
    """Compatibility wrapper for legacy tests/monkeypatching."""
    return assemble_vacuum_settings(
        cli_vacuum=cli_vacuum,
        yaml_maintenance=yaml_maintenance,
    )


def _assemble_runtime_config(
    *,
    ctx: PipelineRunContext,
    heartbeat_interval: int,
    vacuum: VacuumSettings,
    health_check_mode: Literal["strict", "probe"],
) -> RuntimeConfig:
    """Compatibility wrapper for legacy tests/monkeypatching."""
    return assemble_runtime_config(
        ctx=ctx,
        heartbeat_interval=heartbeat_interval,
        vacuum=vacuum,
        health_check_mode=health_check_mode,
    )


def _assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
) -> InputFilterConfig | None:
    """Compatibility wrapper for legacy tests/monkeypatching."""
    return assemble_filter_config(
        yaml_filter=yaml_filter,
        ctx=ctx,
        test_mode=test_mode,
        filter_builder=FilterConfigBuilder,
    )


def _assemble_cached_bronze_context(ctx: PipelineRunContext) -> CachedBronzeContext:
    """Compatibility wrapper for legacy tests/monkeypatching."""
    return assemble_cached_bronze_context(ctx)


def _build_observability_bundle(
    *,
    pipeline: str,
    run_id: RunID,
    settings: Settings,
    log_level: str = "INFO",
) -> ObservabilityBundle:
    """Compatibility wrapper keeping patch-points in this module."""
    return build_observability_bundle(
        pipeline=pipeline,
        run_id=run_id,
        settings=settings,
        log_level=log_level,
        logger_factory=UnifiedLogger,
        tracer_factory=OpenTelemetryTracer,
        metrics_factory=PrometheusMetrics,
        noop_tracing_factory=NoOpTracing,
        noop_metrics_factory=NoOpMetrics,
        dq_monitor_factory=DataQualityMonitor,
    )


def _validate_pk_contract(config: PipelineYamlConfig) -> None:
    """Compatibility wrapper for legacy tests/monkeypatching."""
    validate_pk_contract(config)


def _resolve_health_check_mode(*, settings: Settings) -> Literal["strict", "probe"]:
    """Compatibility wrapper for legacy tests/monkeypatching."""
    return resolve_health_check_mode(settings=settings)


def _resolve_filter_batch_size(yaml_config: PipelineYamlConfig) -> int | None:
    """Compatibility wrapper for legacy tests/monkeypatching."""
    return resolve_filter_batch_size(
        yaml_config,
        load_source_config_fn=load_source_config,
    )


def _initialize_registry(
    *,
    registry: PipelineRegistry | None,
    get_default_registry_fn: Callable[[], PipelineRegistry],
    register_all_providers_fn: Callable[[], None],
    register_all_pipelines_fn: Callable[..., None],
) -> PipelineRegistry:
    """Initialize provider/pipeline registry with optional explicit registry."""
    effective_registry = registry if registry is not None else get_default_registry_fn()
    register_all_providers_fn()
    register_all_pipelines_fn(registry=registry)
    return effective_registry


def _prepare_runner_inputs(
    *,
    ctx: PipelineRunContext,
    get_settings_fn: Callable[[], Settings],
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    build_observability_bundle_fn: Callable[..., ObservabilityBundle],
    assemble_vacuum_settings_fn: Callable[..., VacuumSettings],
    assemble_runtime_config_fn: Callable[..., RuntimeConfig],
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None],
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ],
) -> _RunnerInputs:
    """Compatibility wrapper delegating heavy input-resolution flow."""
    return prepare_runner_inputs(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=build_observability_bundle_fn,
        assemble_vacuum_settings_fn=assemble_vacuum_settings_fn,
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        assemble_filter_config_fn=assemble_filter_config_fn,
        assemble_cached_bronze_context_fn=assemble_cached_bronze_context_fn,
        load_source_config_fn=load_source_config,
    )


def _create_runner_from_factory(
    *,
    factory: PipelineFactoryPort,
    ctx: PipelineRunContext,
    inputs: _RunnerInputs,
) -> PipelineRunner:
    return cast(
        "PipelineRunner",
        factory.create_runner(
            run_id=ctx.run_id,
            runtime=inputs.runtime_config,
            settings=inputs.settings,
            observability=inputs.observability,
            filter_config=inputs.filter_config,
            config=inputs.yaml_config,
            cached_bronze=inputs.cached_bronze,
            debug_port=ctx.debug_port,
        ),
    )


def build_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
    *,
    get_default_registry_fn: Callable[[], PipelineRegistry] = get_default_registry,
    register_all_providers_fn: Callable[[], None] = register_all_providers,
    register_all_pipelines_fn: Callable[..., None] = register_all_pipelines,
    get_settings_fn: Callable[[], Settings] = get_settings,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig] = load_pipeline_config,
    build_observability_bundle_fn: Callable[
        ..., ObservabilityBundle
    ] = _build_observability_bundle,
    assemble_vacuum_settings_fn: Callable[
        ..., VacuumSettings
    ] = _assemble_vacuum_settings,
    assemble_runtime_config_fn: Callable[..., RuntimeConfig] = _assemble_runtime_config,
    assemble_filter_config_fn: Callable[
        ..., InputFilterConfig | None
    ] = _assemble_filter_config,
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ] = _assemble_cached_bronze_context,
) -> PipelineRunner:
    """Assemble and return a fully configured ``PipelineRunner``.

    Args:
        ctx: Pipeline run context containing pipeline name, run type, and execution options.
        registry: Optional PipelineRegistry for test isolation; uses default when None.
        get_default_registry_fn: Callable returning the global PipelineRegistry.
        register_all_providers_fn: Callable registering all provider adapters.
        register_all_pipelines_fn: Callable registering all pipeline factories.
        get_settings_fn: Callable returning global application Settings.
        load_pipeline_config_fn: Callable loading PipelineYamlConfig by pipeline name.
        build_observability_bundle_fn: Callable returning an ObservabilityBundle.
        assemble_vacuum_settings_fn: Callable merging CLI and YAML vacuum settings.
        assemble_runtime_config_fn: Callable building RuntimeConfig from context.
        assemble_filter_config_fn: Callable building InputFilterConfig from YAML and CLI.
        assemble_cached_bronze_context_fn: Callable resolving cached bronze context.

    Returns:
        Fully configured PipelineRunner ready for execution.
    """
    effective_registry = _initialize_registry(
        registry=registry,
        get_default_registry_fn=get_default_registry_fn,
        register_all_providers_fn=register_all_providers_fn,
        register_all_pipelines_fn=register_all_pipelines_fn,
    )
    inputs = _prepare_runner_inputs(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
        load_pipeline_config_fn=load_pipeline_config_fn,
        build_observability_bundle_fn=build_observability_bundle_fn,
        assemble_vacuum_settings_fn=assemble_vacuum_settings_fn,
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        assemble_filter_config_fn=assemble_filter_config_fn,
        assemble_cached_bronze_context_fn=assemble_cached_bronze_context_fn,
    )
    return _create_runner_from_factory(
        factory=effective_registry.get(ctx.pipeline_name).factory,
        ctx=ctx,
        inputs=inputs,
    )
