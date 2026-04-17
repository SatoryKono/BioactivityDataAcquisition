"""Runtime runner input resolution for pipeline bootstrap.

Resolves and assembles all dependencies required to construct a pipeline
runner: settings, YAML config, observability, runtime config, filter config,
and cached Bronze context. Acts as the composition entry point that wires
CLI arguments and YAML configuration into domain-level ``RunnerInputs``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, Literal, Protocol, cast

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders.config_access import (
    load_source_config,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    build_runtime_config as _build_runtime_config,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    log_cached_bronze as _log_cached_bronze,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    log_filter_config as _log_filter_config,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    resolve_health_check_mode_policy as _resolve_health_check_mode_policy,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    resolve_runtime_projection as _resolve_runtime_projection,
)
from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.domain.context import (
        CachedBronzeContext,
        PipelineRunContext,
    )
    from bioetl.domain.context import VacuumSettings as CliVacuumSettings
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterYamlConfig as YamlInputFilter,
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
class ResolvedVacuumSettings:
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
    "ResolvedVacuumSettings",
    "RunnerInputs",
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

_DEFAULT_HEALTH_CHECK_MODE: Literal["strict", "probe"] = "strict"


def _apply_tracing_override(
    *,
    settings: Settings,
    enabled: bool | None,
) -> Settings:
    """Return settings with an optional runtime tracing override applied."""
    if enabled is None:
        return settings

    observability = getattr(settings, "observability", None)
    if observability is None:
        return settings

    if hasattr(settings, "model_copy") and hasattr(observability, "model_copy"):
        updated_observability = observability.model_copy(
            update={"tracing_enabled": enabled}
        )
        copied_settings: Settings = settings.model_copy(
            update={"observability": updated_observability}
        )
        return copied_settings

    namespace_settings = SimpleNamespace(**vars(settings))
    namespace_observability = SimpleNamespace(**vars(observability))
    namespace_observability.tracing_enabled = enabled
    namespace_settings.observability = namespace_observability
    return cast("Settings", namespace_settings)


def assemble_vacuum_settings(
    *,
    cli_vacuum: CliVacuumSettings,
    yaml_maintenance: MaintenanceConfig,
) -> ResolvedVacuumSettings:
    """Merge CLI and YAML vacuum settings into resolved vacuum settings."""
    enabled = (
        cli_vacuum.enabled
        if cli_vacuum.enabled is not None
        else yaml_maintenance.auto_vacuum
    )
    retention = (
        cli_vacuum.retention_days
        if cli_vacuum.enabled is not None
        else yaml_maintenance.vacuum_retention_days
    )
    return ResolvedVacuumSettings(enabled=enabled, retention_days=retention)


def assemble_runtime_config(
    *,
    ctx: PipelineRunContext,
    heartbeat_interval: int,
    vacuum: ResolvedVacuumSettings,
    health_check_mode: Literal["strict", "probe"],
    skip_gold: bool,
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
        exact_replay=getattr(ctx, "exact_replay", False),
        replay_anchor_date=(
            ctx.cached_bronze.bronze_date
            if getattr(ctx, "exact_replay", False)
            else None
        ),
        vacuum_after_run=vacuum.enabled,
        vacuum_retention_days=vacuum.retention_days,
        skip_gold=skip_gold,
        health_check_mode=health_check_mode,
    )


def assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
    filter_builder: type[FilterConfigBuilder] = FilterConfigBuilder,
) -> InputFilterConfig | None:
    """Build ``InputFilterConfig`` from YAML and CLI filter inputs."""
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
    """Fail-fast validation for PK configuration consistency."""
    business_primary_keys = tuple(getattr(config, "business_primary_keys", ()) or ())
    technical_primary_key = getattr(config, "technical_primary_key", "entity_id")

    if not business_primary_keys:
        raise ValueError("business_primary_keys must be non-empty")
    if not technical_primary_key:
        raise ValueError("technical_primary_key must be non-empty")


def resolve_health_check_mode(*, settings: Settings) -> Literal["strict", "probe"]:
    """Resolve runtime health check mode from settings."""
    return cast(
        Literal["strict", "probe"],
        _resolve_health_check_mode_policy(
            settings=settings,
            default_health_check_mode=_DEFAULT_HEALTH_CHECK_MODE,
        ),
    )


def resolve_filter_batch_size(
    yaml_config: PipelineYamlConfig,
    *,
    load_source_config_fn: Callable[..., object] | None = None,
) -> int | None:
    """Resolve batch size override when filter mode is active."""
    filter_batch_size = getattr(yaml_config, "filter_batch_size", None)
    if isinstance(filter_batch_size, int):
        return filter_batch_size
    source_loader = (
        load_source_config if load_source_config_fn is None else load_source_config_fn
    )
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
    """Adjust pipeline batch size to source ID-batch size when filter is enabled."""
    filter_batch_size = resolve_filter_batch_size(
        yaml_config, load_source_config_fn=load_source_config_fn
    )
    if filter_config and filter_batch_size is not None:
        observability.logger.info(
            "batch_size_auto_adjusted",
            original=yaml_config.batch_size,
            adjusted=filter_batch_size,
            reason="input_filter_active",
        )
        yaml_config.batch_size = filter_batch_size


def prepare_runner_inputs(
    *,
    ctx: PipelineRunContext,
    get_settings_fn: Callable[[], Settings],
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    build_observability_bundle_fn: Callable[..., ObservabilityBundle],
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings],
    assemble_runtime_config_fn: Callable[..., RuntimeConfig],
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None],
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ],
    load_source_config_fn: Callable[..., object] | None = None,
) -> RunnerInputs:
    """Resolve runtime settings/config/observability into runner constructor inputs."""
    settings = _apply_tracing_override(
        settings=get_settings_fn(),
        enabled=getattr(ctx, "tracing_enabled_override", None),
    )
    yaml_config = load_pipeline_config_fn(ctx.pipeline_name)
    validate_pk_contract(yaml_config)
    observability = build_observability_bundle_fn(
        pipeline=ctx.pipeline_name,
        run_id=ctx.run_id,
        settings=settings,
        log_level=ctx.log_level,
    )
    vacuum = assemble_vacuum_settings_fn(
        cli_vacuum=ctx.vacuum, yaml_maintenance=yaml_config.maintenance
    )
    runtime_projection = _resolve_runtime_projection(
        ctx=ctx,
        settings=settings,
        yaml_config=yaml_config,
        observability=observability,
        default_health_check_mode=_DEFAULT_HEALTH_CHECK_MODE,
    )
    runtime_config = _build_runtime_config(
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        ctx=ctx,
        vacuum=vacuum,
        runtime_projection=runtime_projection,
    )
    filter_config = assemble_filter_config_fn(
        yaml_filter=yaml_config.input_filter,
        ctx=ctx,
        test_mode=settings.test_mode,
    )
    _log_filter_config(
        observability=observability,
        filter_config=filter_config,
        from_cli=ctx.input_filter.enabled,
    )
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
