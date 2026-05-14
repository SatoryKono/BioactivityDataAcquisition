"""Public runtime input resolver facade."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders._exact_replay_cached_bronze_context import (
    bind_cached_bronze_context as _bind_cached_bronze_context,
)
from bioetl.composition.runtime_builders._exact_replay_cached_bronze_context import (
    resolve_exact_replay_cached_bronze_context as _resolve_exact_replay_cached_bronze_context,
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
from bioetl.composition.runtime_builders.inputs_resolution_orchestration import (
    resolve_runner_filter_config as _resolve_runner_filter_config,
)
from bioetl.composition.runtime_builders.inputs_resolution_orchestration import (
    resolve_runner_runtime_config as _resolve_runner_runtime_config,
)
from bioetl.composition.runtime_builders.inputs_resolution_orchestration import (
    validate_runner_data_root_policy as _validate_runner_data_root_policy,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    log_cached_bronze as _log_cached_bronze,
)
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    resolve_health_check_mode_policy as _resolve_health_check_mode_policy,
)
from bioetl.composition.runtime_builders.inputs_runtime_models import (
    ResolvedVacuumSettings,
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


def _resolve_settings_for_runner(
    *,
    ctx: PipelineRunContext,
    get_settings_fn: Callable[[], Settings],
) -> Settings:
    """Apply runtime tracing overrides before building runner inputs."""
    return _apply_tracing_override_impl(
        settings=get_settings_fn(),
        enabled=getattr(ctx, "tracing_enabled_override", None),
    )


def _resolve_required_persistence_profile(settings: Settings) -> str:
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    return getattr(
        control_plane,
        "required_persistence_profile",
        "degraded_observable",
    )


def _resolve_effective_context(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    assemble_cached_bronze_context_fn: Callable[
        [PipelineRunContext], CachedBronzeContext
    ],
) -> tuple[PipelineRunContext, CachedBronzeContext]:
    """Resolve exact-replay cached Bronze state and bind it into the context."""
    cached_bronze = _resolve_exact_replay_cached_bronze_context(
        ctx=ctx,
        settings=settings,
        cached_bronze=assemble_cached_bronze_context_fn(ctx),
    )
    return _bind_cached_bronze_context(ctx, cached_bronze), cached_bronze


def _load_runner_yaml_config(
    *,
    pipeline_name: str,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
) -> PipelineYamlConfig:
    """Load and validate the pipeline contract used for runner assembly."""
    yaml_config = load_pipeline_config_fn(pipeline_name)
    validate_pk_contract(yaml_config)
    return yaml_config


def _build_runner_observability(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    yaml_config: PipelineYamlConfig,
    build_observability_bundle_fn: Callable[..., ObservabilityBundle],
) -> ObservabilityBundle:
    """Create the observability bundle for one effective runner context."""
    return build_observability_bundle_fn(
        pipeline=ctx.pipeline_name,
        run_id=ctx.run_id,
        settings=settings,
        log_level=ctx.log_level,
        yaml_config=yaml_config,
        skip_gold=bool(getattr(ctx, "skip_gold", False)),
    )


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
    settings = _resolve_settings_for_runner(
        ctx=ctx,
        get_settings_fn=get_settings_fn,
    )
    _validate_runner_data_root_policy(
        ctx=ctx,
        settings=settings,
        required_persistence_profile=_resolve_required_persistence_profile(settings),
    )
    effective_ctx, cached_bronze = _resolve_effective_context(
        ctx=ctx,
        settings=settings,
        assemble_cached_bronze_context_fn=assemble_cached_bronze_context_fn,
    )
    yaml_config = _load_runner_yaml_config(
        pipeline_name=ctx.pipeline_name,
        load_pipeline_config_fn=load_pipeline_config_fn,
    )
    observability = _build_runner_observability(
        ctx=effective_ctx,
        settings=settings,
        yaml_config=yaml_config,
        build_observability_bundle_fn=build_observability_bundle_fn,
    )
    runtime_config = _resolve_runner_runtime_config(
        ctx=effective_ctx,
        settings=settings,
        yaml_config=yaml_config,
        observability=observability,
        default_health_check_mode=_DEFAULT_HEALTH_CHECK_MODE,
        assemble_vacuum_settings_fn=assemble_vacuum_settings_fn,
        assemble_runtime_config_fn=assemble_runtime_config_fn,
    )
    filter_config = _resolve_runner_filter_config(
        ctx=effective_ctx,
        settings=settings,
        yaml_config=yaml_config,
        observability=observability,
        assemble_filter_config_fn=assemble_filter_config_fn,
        adjust_batch_size_for_filter_fn=adjust_batch_size_for_filter,
        load_source_config_fn=load_source_config_fn,
    )
    _log_cached_bronze(observability=observability, cached_bronze=cached_bronze)
    return RunnerInputs(
        settings=settings,
        yaml_config=yaml_config,
        observability=observability,
        runtime_config=runtime_config,
        filter_config=filter_config,
        cached_bronze=cached_bronze,
    )
