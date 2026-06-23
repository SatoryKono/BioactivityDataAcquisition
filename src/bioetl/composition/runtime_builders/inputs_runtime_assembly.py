"""Owner-only runtime input assembly helpers behind the public inputs facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    adjust_batch_size_for_filter_impl as _adjust_batch_size_for_filter_impl,
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
    resolve_health_check_mode_policy as _resolve_health_check_mode_policy,
)
from bioetl.composition.runtime_builders.inputs_runtime_models import (
    ResolvedVacuumSettings,
)
from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.domain.context import VacuumSettings as CliVacuumSettings
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterYamlConfig as YamlInputFilter,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        MaintenanceConfig,
        PipelineYamlConfig,
    )

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


__all__ = [
    "ResolvedVacuumSettings",
    "adjust_batch_size_for_filter",
    "assemble_cached_bronze_context",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
    "resolve_filter_batch_size",
    "resolve_health_check_mode",
    "validate_pk_contract",
]
