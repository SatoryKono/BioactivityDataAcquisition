"""Support helpers for resolving runtime builder inputs."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import TYPE_CHECKING, Literal, Protocol, cast

from bioetl.domain.config import RuntimeConfig
from bioetl.infrastructure.config.silver_filter_migration import (
    resolve_silver_filter_compatibility_mode,
)

# Keep typing protocols imported at runtime because these helpers define them
# in module scope and the Windows shared-drive bytecode cache can otherwise lag.

if TYPE_CHECKING:
    from bioetl.composition.builders import FilterConfigBuilder
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
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


class PaginationConfigLike(Protocol):
    id_batch_size: object


class SourceConfigLike(Protocol):
    pagination: PaginationConfigLike


def apply_tracing_override(
    *,
    settings: Settings,
    enabled: bool | None,
) -> Settings:
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


def assemble_vacuum_settings_impl(
    *,
    cli_vacuum: CliVacuumSettings,
    yaml_maintenance: MaintenanceConfig,
) -> tuple[bool, int]:
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
    return enabled, retention


def assemble_runtime_config_impl(
    *,
    ctx: PipelineRunContext,
    heartbeat_interval: int,
    vacuum_enabled: bool,
    vacuum_retention_days: int,
    health_check_mode: Literal["strict", "probe"],
    skip_gold: bool,
) -> RuntimeConfig:
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
        vacuum_after_run=vacuum_enabled,
        vacuum_retention_days=vacuum_retention_days,
        skip_gold=skip_gold,
        health_check_mode=health_check_mode,
        silver_filter_compatibility_mode=resolve_silver_filter_compatibility_mode(),
    )


def assemble_filter_config_impl(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
    filter_builder: type[FilterConfigBuilder],
) -> InputFilterConfig | None:
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


def assemble_cached_bronze_context_impl(ctx: PipelineRunContext) -> CachedBronzeContext:
    return ctx.cached_bronze


def validate_pk_contract_impl(config: PipelineYamlConfig) -> None:
    business_primary_keys = tuple(getattr(config, "business_primary_keys", ()) or ())
    technical_primary_key = getattr(config, "technical_primary_key", "entity_id")

    if not business_primary_keys:
        raise ValueError("business_primary_keys must be non-empty")
    if not technical_primary_key:
        raise ValueError("technical_primary_key must be non-empty")


def resolve_filter_batch_size_impl(
    yaml_config: PipelineYamlConfig,
    *,
    source_loader: Callable[..., object],
) -> int | None:
    try:
        source_cfg = cast(SourceConfigLike, source_loader(yaml_config.provider))
        batch_size = source_cfg.pagination.id_batch_size
        return batch_size if isinstance(batch_size, int) else None
    except (ValueError, AttributeError):
        return None


def adjust_batch_size_for_filter_impl(
    *,
    yaml_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None,
    observability: ObservabilityBundle,
    filter_batch_size: int | None,
) -> None:
    if filter_config and filter_batch_size is not None:
        observability.logger.info(
            "batch_size_auto_adjusted",
            original=yaml_config.batch_size,
            adjusted=filter_batch_size,
            reason="input_filter_active",
        )
        yaml_config.batch_size = filter_batch_size
