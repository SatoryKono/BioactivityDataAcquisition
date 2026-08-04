"""Orchestration helpers for preparing runtime runner inputs."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders.inputs_runtime_helpers import (
    build_runtime_config as _build_runtime_config,
    log_filter_config as _log_filter_config,
    resolve_runtime_projection as _resolve_runtime_projection,
)
from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_runtime_models import (
        ResolvedVacuumSettings,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def validate_runner_data_root_policy(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    required_persistence_profile: str,
) -> None:
    from bioetl.composition.runtime_builders._runner_control_plane_data_root_policy import (
        validate_strict_data_root_policy as _validate_strict_data_root_policy,
    )

    _validate_strict_data_root_policy(
        settings=settings,
        required_profile=required_persistence_profile,
        exact_replay=bool(getattr(ctx, "exact_replay", False)),
    )


def resolve_runner_runtime_config(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    yaml_config: PipelineYamlConfig,
    observability: ObservabilityBundle,
    default_health_check_mode: Literal["strict", "probe"],
    assemble_vacuum_settings_fn: Callable[..., ResolvedVacuumSettings],
    assemble_runtime_config_fn: Callable[..., RuntimeConfig],
) -> RuntimeConfig:
    vacuum = assemble_vacuum_settings_fn(
        cli_vacuum=ctx.vacuum,
        yaml_maintenance=yaml_config.maintenance,
    )
    runtime_projection = _resolve_runtime_projection(
        ctx=ctx,
        settings=settings,
        yaml_config=yaml_config,
        observability=observability,
        default_health_check_mode=default_health_check_mode,
    )
    return _build_runtime_config(
        assemble_runtime_config_fn=assemble_runtime_config_fn,
        ctx=ctx,
        vacuum=vacuum,
        runtime_projection=runtime_projection,
    )


def resolve_runner_filter_config(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    yaml_config: PipelineYamlConfig,
    observability: ObservabilityBundle,
    assemble_filter_config_fn: Callable[..., InputFilterConfig | None],
    adjust_batch_size_for_filter_fn: Callable[..., None],
    load_source_config_fn: Callable[..., object] | None,
) -> InputFilterConfig | None:
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
    adjust_batch_size_for_filter_fn(
        yaml_config=yaml_config,
        filter_config=filter_config,
        observability=observability,
        load_source_config_fn=load_source_config_fn,
    )
    return filter_config
