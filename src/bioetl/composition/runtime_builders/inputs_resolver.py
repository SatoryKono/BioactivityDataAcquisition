"""Public runtime input resolver facade."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders.inputs_runtime_models import (
    ResolvedVacuumSettings,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    adjust_batch_size_for_filter_impl as _adjust_batch_size_for_filter_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    apply_tracing_override as _apply_tracing_override_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    assemble_cached_bronze_context_impl as _assemble_cached_bronze_context_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    assemble_filter_config_impl as _assemble_filter_config_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    assemble_runtime_config_impl as _assemble_runtime_config_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    assemble_vacuum_settings_impl as _assemble_vacuum_settings_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    resolve_filter_batch_size_impl as _resolve_filter_batch_size_impl,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    validate_pk_contract_impl as _validate_pk_contract_impl,
)
from bioetl.composition.runtime_builders.config_access import load_source_config
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


@dataclass(frozen=True, slots=True)
class RunnerInputs:
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


def assemble_vacuum_settings(
    *,
    cli_vacuum: CliVacuumSettings,
    yaml_maintenance: MaintenanceConfig,
) -> ResolvedVacuumSettings:
    enabled, retention_days = _assemble_vacuum_settings_impl(
        cli_vacuum=cli_vacuum,
        yaml_maintenance=yaml_maintenance,
    )
    return ResolvedVacuumSettings(
        enabled=enabled,
        retention_days=retention_days,
    )


def assemble_runtime_config(
    *,
    ctx: PipelineRunContext,
    heartbeat_interval: int,
    vacuum: ResolvedVacuumSettings,
    health_check_mode: Literal["strict", "probe"],
    skip_gold: bool,
) -> RuntimeConfig:
    return _assemble_runtime_config_impl(
        ctx=ctx,
        heartbeat_interval=heartbeat_interval,
        vacuum_enabled=vacuum.enabled,
        vacuum_retention_days=vacuum.retention_days,
        health_check_mode=health_check_mode,
        skip_gold=skip_gold,
    )


def assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
    filter_builder: type[FilterConfigBuilder] = FilterConfigBuilder,
) -> InputFilterConfig | None:
    return _assemble_filter_config_impl(
        yaml_filter=yaml_filter,
        ctx=ctx,
        test_mode=test_mode,
        filter_builder=filter_builder,
    )


def assemble_cached_bronze_context(ctx: PipelineRunContext) -> CachedBronzeContext:
    return _assemble_cached_bronze_context_impl(ctx)


def validate_pk_contract(config: PipelineYamlConfig) -> None:
    _validate_pk_contract_impl(config)


def resolve_health_check_mode(*, settings: Settings) -> Literal["strict", "probe"]:
    return _resolve_health_check_mode_policy(
        settings=settings,
        default_health_check_mode=_DEFAULT_HEALTH_CHECK_MODE,
    )


def resolve_filter_batch_size(
    yaml_config: PipelineYamlConfig,
    *,
    load_source_config_fn: Callable[..., object] | None = None,
) -> int | None:
    source_loader = (
        load_source_config if load_source_config_fn is None else load_source_config_fn
    )
    return _resolve_filter_batch_size_impl(
        yaml_config,
        source_loader=source_loader,
    )


def adjust_batch_size_for_filter(
    *,
    yaml_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None,
    observability: ObservabilityBundle,
    load_source_config_fn: Callable[..., object] | None = None,
) -> None:
    _adjust_batch_size_for_filter_impl(
        yaml_config=yaml_config,
        filter_config=filter_config,
        observability=observability,
        filter_batch_size=resolve_filter_batch_size(
            yaml_config,
            load_source_config_fn=load_source_config_fn,
        ),
    )


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
    settings = _apply_tracing_override_impl(
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
        yaml_config=yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
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
