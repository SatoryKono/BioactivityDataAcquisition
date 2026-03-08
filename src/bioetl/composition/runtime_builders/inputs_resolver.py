"""Sub-service for runtime runner input resolution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, cast

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.config import RuntimeConfig
from bioetl.infrastructure.config import load_source_config

if TYPE_CHECKING:
    from bioetl.domain.context import (
        CachedBronzeContext,
        PipelineRunContext,
        VacuumSettings,
    )
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterConfig as YamlInputFilter,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        MaintenanceConfig,
        PipelineYamlConfig,
    )


class _PaginationConfigLike(Protocol):
    id_batch_size: object


class _SourceConfigLike(Protocol):
    pagination: _PaginationConfigLike


@dataclass(frozen=True, slots=True)
class VacuumSettings:
    """Resolved vacuum settings after merging CLI and YAML config."""

    enabled: bool
    retention_days: int


@dataclass(frozen=True, slots=True)
class RunnerInputs:
    """Resolved dependency set required for pipeline runner creation."""

    settings: Settings
    yaml_config: PipelineYamlConfig
    observability: ObservabilityBundle
    runtime_config: RuntimeConfig
    filter_config: InputFilterConfig | None
    cached_bronze: CachedBronzeContext


__all__ = [
    "RunnerInputs",
    "VacuumSettings",
    "adjust_batch_size_for_filter",
    "assemble_cached_bronze_context",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
    "prepare_runner_inputs",
    "resolve_filter_batch_size",
    "resolve_health_check_mode",
    "validate_pk_contract",
]


def assemble_vacuum_settings(
    *,
    cli_vacuum: VacuumSettings,
    yaml_maintenance: MaintenanceConfig,
) -> VacuumSettings:
    """Merge CLI and YAML vacuum settings.

    Args:
        cli_vacuum: Vacuum configuration from CLI (tri-state enabled flag).
        yaml_maintenance: Maintenance configuration from pipeline YAML defaults.

    Returns:
        VacuumSettings with resolved enabled flag and retention days.
    """
    enabled = cli_vacuum.enabled if cli_vacuum.enabled is not None else yaml_maintenance.auto_vacuum
    retention = cli_vacuum.retention_days if cli_vacuum.enabled is not None else yaml_maintenance.vacuum_retention_days
    return VacuumSettings(enabled=enabled, retention_days=retention)


def assemble_runtime_config(
    *,
    ctx: PipelineRunContext,
    heartbeat_interval: int,
    vacuum: VacuumSettings,
    health_check_mode: Literal["strict", "probe"],
) -> RuntimeConfig:
    """Build ``RuntimeConfig`` from run context and resolved vacuum settings.

    Args:
        ctx: Pipeline run context providing run type, limit, query, and other options.
        heartbeat_interval: Interval in seconds for lock heartbeat updates.
        vacuum: Resolved vacuum settings (enabled flag and retention days).
        health_check_mode: Health check enforcement mode; 'strict' raises on failure.

    Returns:
        Immutable RuntimeConfig instance for this pipeline run.
    """
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


def assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
    filter_builder: type[FilterConfigBuilder] = FilterConfigBuilder,
) -> InputFilterConfig | None:
    """Build ``InputFilterConfig`` from YAML and CLI filter inputs.

    Args:
        yaml_filter: Filter configuration from pipeline YAML.
        ctx: Pipeline run context containing CLI filter settings and flags.
        test_mode: If True, YAML-based filters are disabled.
        filter_builder: FilterConfigBuilder class used to build the config. Defaults
            to FilterConfigBuilder.

    Returns:
        Configured InputFilterConfig, or None if filtering is disabled.
    """
    inp_filter = ctx.input_filter
    enabled = inp_filter.enabled
    return filter_builder.build(
        yaml_filter=yaml_filter,
        cli_csv=inp_filter.source_path if enabled else None,
        cli_column=inp_filter.column_name if enabled else None,
        cli_field=inp_filter.filter_field if enabled else None,
        cli_fallback_column=inp_filter.fallback_column if enabled else None,
        test_mode=test_mode or ctx.ignore_yaml_filter,
        direct_filter_ids=inp_filter.filter_ids,
        direct_fallback_mapping=inp_filter.fallback_mapping,
        direct_multi_filter_ids=inp_filter.multi_filter_ids,
        direct_valid_combinations=inp_filter.valid_combinations,
    )


def assemble_cached_bronze_context(ctx: PipelineRunContext) -> CachedBronzeContext:
    """Resolve cached-bronze context from run context."""
    return ctx.cached_bronze


def validate_pk_contract(config: PipelineYamlConfig) -> None:
    """Fail-fast validation for PK configuration consistency.

    Args:
        config: Pipeline YAML configuration to validate for primary key consistency.

    Raises:
        ValueError: If business_primary_keys is empty, PKs are mismatched, or
            technical_primary_key is empty.
    """
    business_primary_keys = tuple(getattr(config, "business_primary_keys", ()) or ())
    legacy_primary_keys = getattr(config, "primary_keys", None)
    technical_primary_key = getattr(config, "technical_primary_key", "entity_id")

    if not business_primary_keys:
        raise ValueError("business_primary_keys must be non-empty")
    if legacy_primary_keys is not None and tuple(legacy_primary_keys) != business_primary_keys:
        raise ValueError(
            "PK mismatch: legacy primary_keys differs from business_primary_keys; "
            "fix pipeline config naming"
        )
    if not technical_primary_key:
        raise ValueError("technical_primary_key must be non-empty")


def resolve_health_check_mode(*, settings: Settings) -> Literal["strict", "probe"]:
    """Resolve runtime health check mode from settings."""
    if settings.test_mode:
        return "probe"
    return cast(Literal["strict", "probe"], getattr(settings.pipeline, "health_check_mode", "strict"))


def _log_filter_config(
    *,
    observability: ObservabilityBundle,
    filter_config: InputFilterConfig | None,
    from_cli: bool,
) -> None:
    if not filter_config:
        return
    observability.logger.info(
        "input_filter_enabled",
        csv_path=filter_config.source_path,
        column=filter_config.column_name,
        filter_field=filter_config.filter_field,
        source="cli" if from_cli else "config",
    )


def resolve_filter_batch_size(
    yaml_config: PipelineYamlConfig,
    *,
    load_source_config_fn: Callable[..., object] | None = None,
) -> int | None:
    """Resolve batch size override when filter mode is active.

    Args:
        yaml_config: Pipeline YAML configuration providing filter_batch_size and provider.
        load_source_config_fn: Optional callable to load source config; uses default
            load_source_config when None.

    Returns:
        Integer batch size if configured, None otherwise.
    """
    filter_batch_size = getattr(yaml_config, "filter_batch_size", None)
    if isinstance(filter_batch_size, int):
        return filter_batch_size
    source_loader = load_source_config if load_source_config_fn is None else load_source_config_fn
    try:
        source_cfg = cast(_SourceConfigLike, source_loader(yaml_config.provider))
        batch_size = source_cfg.pagination.id_batch_size
        return batch_size if isinstance(batch_size, int) else None
    except (ValueError, AttributeError):
        return None


def adjust_batch_size_for_filter(
    *,
    yaml_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None,
    observability: ObservabilityBundle,
    load_source_config_fn: Callable[..., object] | None = None,
) -> None:
    """Adjust pipeline batch size to source ID-batch size when filter is enabled.

    Args:
        yaml_config: Pipeline YAML configuration; batch_size is mutated in-place if adjusted.
        filter_config: Active filter configuration; no adjustment if None.
        observability: ObservabilityBundle used to log batch size adjustments.
        load_source_config_fn: Optional callable to load source config for batch size lookup.
    """
    filter_batch_size = resolve_filter_batch_size(yaml_config, load_source_config_fn=load_source_config_fn)
    if filter_config and filter_batch_size is not None:
        observability.logger.info(
            "batch_size_auto_adjusted",
            original=yaml_config.batch_size,
            adjusted=filter_batch_size,
            reason="input_filter_active",
        )
        yaml_config.batch_size = filter_batch_size


def _log_cached_bronze(
    *,
    observability: ObservabilityBundle,
    cached_bronze: CachedBronzeContext,
) -> None:
    if not cached_bronze.enabled:
        return
    observability.logger.info(
        "cached_bronze_mode_enabled",
        bronze_path=cached_bronze.bronze_path,
        bronze_date=cached_bronze.bronze_date,
    )


def prepare_runner_inputs(
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
    load_source_config_fn: Callable[..., object] | None = None,
) -> RunnerInputs:
    """Resolve runtime settings/config/observability into runner constructor inputs.

    Args:
        ctx: Pipeline run context with pipeline name, run type, and filter settings.
        get_settings_fn: Callable returning global application Settings.
        load_pipeline_config_fn: Callable returning PipelineYamlConfig for a pipeline name.
        build_observability_bundle_fn: Callable returning an ObservabilityBundle.
        assemble_vacuum_settings_fn: Callable merging CLI and YAML vacuum settings.
        assemble_runtime_config_fn: Callable building RuntimeConfig from context.
        assemble_filter_config_fn: Callable building InputFilterConfig from YAML and CLI.
        assemble_cached_bronze_context_fn: Callable resolving cached bronze context.
        load_source_config_fn: Optional callable to load source config for batch size.

    Returns:
        RunnerInputs bundle with all resolved dependencies for runner construction.
    """
    settings = get_settings_fn()
    yaml_config = load_pipeline_config_fn(ctx.pipeline_name)
    validate_pk_contract(yaml_config)
    observability = build_observability_bundle_fn(
        pipeline=ctx.pipeline_name, run_id=ctx.run_id, settings=settings, log_level=ctx.log_level
    )
    vacuum = assemble_vacuum_settings_fn(cli_vacuum=ctx.vacuum, yaml_maintenance=yaml_config.maintenance)
    runtime_config = assemble_runtime_config_fn(
        ctx=ctx,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
        vacuum=vacuum,
        health_check_mode=resolve_health_check_mode(settings=settings),
    )
    filter_config = assemble_filter_config_fn(
        yaml_filter=yaml_config.input_filter, ctx=ctx, test_mode=settings.test_mode,
    )
    _log_filter_config(observability=observability, filter_config=filter_config, from_cli=ctx.input_filter.enabled)
    adjust_batch_size_for_filter(
        yaml_config=yaml_config,
        filter_config=filter_config,
        observability=observability,
        load_source_config_fn=load_source_config_fn,
    )
    cached_bronze = assemble_cached_bronze_context_fn(ctx)
    _log_cached_bronze(observability=observability, cached_bronze=cached_bronze)
    return RunnerInputs(
        settings=settings,
        yaml_config=yaml_config,
        observability=observability,
        runtime_config=runtime_config,
        filter_config=filter_config,
        cached_bronze=cached_bronze,
    )
