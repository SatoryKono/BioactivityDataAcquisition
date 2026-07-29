"""Internal runtime/logging helpers for runner input resolution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.config import RuntimeConfig

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_runtime_models import (
        ResolvedVacuumSettings,
    )
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class ResolvedRuntimeProjection:
    """Explicit runtime policy projected from settings, CLI context, and YAML."""

    heartbeat_interval: int
    health_check_mode: Literal["strict", "probe"]
    skip_gold: bool


def resolve_heartbeat_interval_policy(*, settings: Settings) -> int:
    """Resolve heartbeat interval from canonical composition settings."""
    return int(settings.pipeline.heartbeat_interval)


def log_filter_config(
    *,
    observability: ObservabilityBundle,
    filter_config: InputFilterConfig | None,
    from_cli: bool,
) -> None:
    """Emit one structured log when input filtering is active."""
    if not filter_config:
        return
    observability.logger.info(
        "input_filter_enabled",
        csv_path=filter_config.source_path,
        column=filter_config.column_name,
        filter_field=filter_config.filter_field,
        source="cli" if from_cli else "config",
    )


def log_cached_bronze(
    *,
    observability: ObservabilityBundle,
    cached_bronze: CachedBronzeContext,
) -> None:
    """Emit one structured log when cached Bronze mode is enabled."""
    if not cached_bronze.enabled:
        return
    observability.logger.info(
        "cached_bronze_mode_enabled",
        bronze_path=cached_bronze.bronze_path,
        bronze_date=cached_bronze.bronze_date,
    )


def is_gold_sink_enabled(yaml_config: PipelineYamlConfig) -> bool:
    """Return whether Gold sink remains enabled in YAML configuration."""
    sink = getattr(yaml_config, "sink", {})
    gold_sink = sink.get("gold") if isinstance(sink, dict) else None
    return gold_sink is None or bool(gold_sink.enabled)


def resolve_skip_gold_policy(
    *,
    ctx: PipelineRunContext,
    yaml_config: PipelineYamlConfig,
    observability: ObservabilityBundle,
) -> bool:
    """Resolve skip-gold policy from CLI intent plus YAML sink availability."""
    if ctx.skip_gold:
        return True
    if is_gold_sink_enabled(yaml_config):
        return False
    observability.logger.info(
        "gold_sink_disabled",
        reason="sink.gold.enabled_false",
        pipeline=getattr(yaml_config, "pipeline_name", None),
    )
    return True


def resolve_health_check_mode_policy(
    *,
    settings: Settings,
    default_health_check_mode: Literal["strict", "probe"],
) -> Literal["strict", "probe"]:
    """Resolve health-check policy from settings with explicit default fallback."""
    if settings.test_mode:
        return "probe"
    configured_mode = getattr(settings.pipeline, "health_check_mode", None)
    if configured_mode in ("strict", "probe"):
        return cast(Literal["strict", "probe"], configured_mode)
    return default_health_check_mode


def resolve_runtime_projection(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    yaml_config: PipelineYamlConfig,
    observability: ObservabilityBundle,
    default_health_check_mode: Literal["strict", "probe"],
) -> ResolvedRuntimeProjection:
    """Resolve explicit runtime policy before RuntimeConfig assembly."""
    return ResolvedRuntimeProjection(
        heartbeat_interval=resolve_heartbeat_interval_policy(settings=settings),
        health_check_mode=resolve_health_check_mode_policy(
            settings=settings,
            default_health_check_mode=default_health_check_mode,
        ),
        skip_gold=resolve_skip_gold_policy(
            ctx=ctx,
            yaml_config=yaml_config,
            observability=observability,
        ),
    )


def build_runtime_config(
    *,
    assemble_runtime_config_fn: Callable[..., RuntimeConfig],
    ctx: PipelineRunContext,
    vacuum: ResolvedVacuumSettings,
    runtime_projection: ResolvedRuntimeProjection,
) -> RuntimeConfig:
    """Build RuntimeConfig from explicit runtime projection values."""
    return assemble_runtime_config_fn(
        ctx=ctx,
        heartbeat_interval=runtime_projection.heartbeat_interval,
        vacuum=vacuum,
        health_check_mode=runtime_projection.health_check_mode,
        skip_gold=runtime_projection.skip_gold,
    )
