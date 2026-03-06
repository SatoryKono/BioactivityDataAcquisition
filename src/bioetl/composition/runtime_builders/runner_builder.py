"""Leaf builder for runtime pipeline runner construction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers.registration import register_all_providers
from bioetl.composition.registry import PipelineRegistry, get_default_registry
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

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import (
        CachedBronzeContext,
        PipelineRunContext,
        VacuumConfig,
    )
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterConfig as YamlInputFilter,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        MaintenanceConfig,
        PipelineYamlConfig,
    )


@dataclass(frozen=True, slots=True)
class VacuumSettings:
    """Resolved vacuum settings after merging CLI and YAML config."""

    enabled: bool
    retention_days: int


__all__ = ["build_pipeline_runner"]


def _assemble_vacuum_settings(
    *,
    cli_vacuum: VacuumConfig,
    yaml_maintenance: MaintenanceConfig,
) -> VacuumSettings:
    """Merge CLI and YAML vacuum settings."""
    if cli_vacuum.enabled is not None:
        return VacuumSettings(
            enabled=cli_vacuum.enabled,
            retention_days=cli_vacuum.retention_days,
        )

    return VacuumSettings(
        enabled=yaml_maintenance.auto_vacuum,
        retention_days=yaml_maintenance.vacuum_retention_days,
    )


def _assemble_runtime_config(
    *,
    ctx: PipelineRunContext,
    heartbeat_interval: int,
    vacuum: VacuumSettings,
    health_check_mode: Literal["strict", "probe"],
) -> RuntimeConfig:
    """Build ``RuntimeConfig`` from run context and resolved vacuum settings."""
    return RuntimeConfig(
        run_type=ctx.run_type,
        resume=ctx.resume,
        start_offset=ctx.start_offset,
        limit=ctx.limit,
        heartbeat_interval=heartbeat_interval,
        query=ctx.query,
        dry_run=ctx.dry_run,
        vacuum_after_run=vacuum.enabled,
        vacuum_retention_days=vacuum.retention_days,
        skip_gold=ctx.skip_gold,
        health_check_mode=health_check_mode,
    )


def _assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
) -> InputFilterConfig | None:
    """Build ``InputFilterConfig`` from YAML and CLI filter inputs."""
    return FilterConfigBuilder.build(
        yaml_filter=yaml_filter,
        cli_csv=ctx.input_filter.source_path if ctx.input_filter.enabled else None,
        cli_column=ctx.input_filter.column_name if ctx.input_filter.enabled else None,
        cli_field=ctx.input_filter.filter_field if ctx.input_filter.enabled else None,
        cli_fallback_column=ctx.input_filter.fallback_column
        if ctx.input_filter.enabled
        else None,
        test_mode=test_mode or ctx.ignore_yaml_filter,
        direct_filter_ids=ctx.input_filter.filter_ids,
        direct_fallback_mapping=ctx.input_filter.fallback_mapping,
        direct_multi_filter_ids=ctx.input_filter.multi_filter_ids,
        direct_valid_combinations=ctx.input_filter.valid_combinations,
    )


def _assemble_cached_bronze_context(ctx: PipelineRunContext) -> CachedBronzeContext:
    return ctx.cached_bronze


def _build_observability_bundle(
    *,
    pipeline: str,
    run_id: RunID,
    settings: Settings,
    log_level: str = "INFO",
) -> ObservabilityBundle:
    logger = UnifiedLogger(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
        json_format=True,
    )
    tracer = (
        OpenTelemetryTracer(service_name="bioetl")
        if settings.observability.tracing_enabled
        else NoOpTracing()
    )
    metrics = (
        PrometheusMetrics()
        if settings.observability.metrics_enabled
        else NoOpMetrics(warn_on_use=False)
    )

    dq_monitor = None
    if settings.observability.dq_monitor_enabled:
        dq_monitor = DataQualityMonitor(
            logger=logger,
            baseline_window=settings.observability.dq_baseline_window,
            z_score_threshold=settings.observability.dq_z_score_threshold,
        )
        dq_monitor.detector.min_baseline_samples = (
            settings.observability.dq_min_baseline_samples
        )
        dq_monitor.detector.set_threshold(
            "error_rate",
            min_value=0.0,
            max_value=settings.observability.dq_error_rate_max,
        )
        dq_monitor.detector.set_threshold(
            "quality_score",
            min_value=settings.observability.dq_quality_score_min,
            max_value=1.0,
        )

    return ObservabilityBundle(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )


def _validate_pk_contract(
    config: PipelineYamlConfig,
) -> None:
    """Fail-fast validation for PK configuration consistency."""
    business_primary_keys = tuple(getattr(config, "business_primary_keys", ()) or ())
    legacy_primary_keys = getattr(config, "primary_keys", None)
    technical_primary_key = getattr(config, "technical_primary_key", "entity_id")

    if not business_primary_keys:
        raise ValueError("business_primary_keys must be non-empty")

    if (
        legacy_primary_keys is not None
        and tuple(legacy_primary_keys) != business_primary_keys
    ):
        raise ValueError(
            "PK mismatch: legacy primary_keys differs from business_primary_keys; "
            "fix pipeline config naming"
        )

    if not technical_primary_key:
        raise ValueError("technical_primary_key must be non-empty")


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
    """Assemble and return a fully configured ``PipelineRunner``."""
    effective_registry = registry if registry is not None else get_default_registry_fn()

    register_all_providers_fn()
    register_all_pipelines_fn(registry=registry)

    settings = get_settings_fn()
    yaml_config = load_pipeline_config_fn(ctx.pipeline_name)
    _validate_pk_contract(yaml_config)

    observability = build_observability_bundle_fn(
        pipeline=ctx.pipeline_name,
        run_id=ctx.run_id,
        settings=settings,
        log_level=ctx.log_level,
    )

    vacuum = assemble_vacuum_settings_fn(
        cli_vacuum=ctx.vacuum,
        yaml_maintenance=yaml_config.maintenance,
    )

    runtime_config = assemble_runtime_config_fn(
        ctx=ctx,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
        vacuum=vacuum,
        health_check_mode=(
            "probe"
            if settings.test_mode
            else getattr(settings.pipeline, "health_check_mode", "strict")
        ),
    )

    filter_config = assemble_filter_config_fn(
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

    # Resolution order:
    # 1. pipeline filter_batch_size (legacy)
    # 2. source pagination.id_batch_size (canonical)
    filter_batch_size = getattr(yaml_config, "filter_batch_size", None)
    if filter_batch_size is None:
        try:
            source_cfg = load_source_config(yaml_config.provider)
            filter_batch_size = source_cfg.pagination.id_batch_size
        except (ValueError, AttributeError):
            pass
    if filter_config and filter_batch_size is not None:
        observability.logger.info(
            "batch_size_auto_adjusted",
            original=yaml_config.batch_size,
            adjusted=filter_batch_size,
            reason="input_filter_active",
        )
        yaml_config.batch_size = filter_batch_size

    cached_bronze = assemble_cached_bronze_context_fn(ctx)

    if cached_bronze.enabled:
        observability.logger.info(
            "cached_bronze_mode_enabled",
            bronze_path=cached_bronze.bronze_path,
            bronze_date=cached_bronze.bronze_date,
        )

    pipeline_def = effective_registry.get(ctx.pipeline_name)
    factory = pipeline_def.factory

    return cast(
        "PipelineRunner",
        factory.create_runner(
            run_id=ctx.run_id,
            runtime=runtime_config,
            settings=settings,
            observability=observability,
            filter_config=filter_config,
            config=yaml_config,
            cached_bronze=cached_bronze,
        ),
    )
