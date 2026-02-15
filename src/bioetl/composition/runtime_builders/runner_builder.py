"""Leaf builder for runtime pipeline runner construction.

This module contains the concrete assembly logic for creating a configured
PipelineRunner without importing from ``bioetl.composition.bootstrap``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers.registration import register_all_providers
from bioetl.composition.registry import PipelineRegistry, get_default_registry
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.ports import NoOpMetrics, NoOpTracing
from bioetl.infrastructure.config import get_settings, load_pipeline_config
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
    from bioetl.infrastructure.config import Settings
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterConfig as YamlInputFilter,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        MaintenanceConfig,
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
) -> RuntimeConfig:
    return RuntimeConfig(
        run_type=ctx.run_type,
        resume=ctx.resume,
        limit=ctx.limit,
        heartbeat_interval=heartbeat_interval,
        query=ctx.query,
        dry_run=ctx.dry_run,
        vacuum_after_run=vacuum.enabled,
        vacuum_retention_days=vacuum.retention_days,
        skip_gold=ctx.skip_gold,
    )


def _assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
) -> InputFilterConfig | None:
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
    ctx: PipelineRunContext,
    settings: Settings,
) -> ObservabilityBundle:
    logger = UnifiedLogger(
        pipeline=pipeline,
        run_id=ctx.run_id,
        log_level=ctx.log_level,
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

    observability = _build_observability_bundle(
        pipeline=ctx.pipeline_name,
        ctx=ctx,
        settings=settings,
    )

    vacuum = _assemble_vacuum_settings(
        cli_vacuum=ctx.vacuum,
        yaml_maintenance=yaml_config.maintenance,
    )

    runtime_config = _assemble_runtime_config(
        ctx=ctx,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
        vacuum=vacuum,
    )

    filter_config = _assemble_filter_config(
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

    cached_bronze = _assemble_cached_bronze_context(ctx)

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
