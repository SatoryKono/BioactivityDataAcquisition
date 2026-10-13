"""Pure assembly helpers for pipeline bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict, Unpack
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.config.runtime import PreflightRuntimeSettings
from bioetl.domain.types import RunType
from bioetl.domain.filtering.silver_filter_identity import (
    resolve_silver_filter_compatibility_mode,
)

from dataclasses import dataclass
from pathlib import Path

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.runtime_builders.inputs_runtime_assembly import (
    ResolvedVacuumSettings,
    assemble_vacuum_settings as _assemble_vacuum_settings,
)
from bioetl.domain.context import CachedBronzeContext
from bioetl.composition.runtime_builders import runner_builder_wiring as wiring

if TYPE_CHECKING:
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.context import VacuumSettings as CliVacuumSettings
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterYamlConfig as YamlInputFilter,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        MaintenanceConfig,
    )

__all__ = [
    "PreflightRuntimeSettings",
    "ResolvedVacuumSettings",
    "RuntimeBootstrapPhases",
    "assemble_cached_bronze_context",
    "assemble_filter_config",
    "assemble_runtime_bootstrap_phases",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
]


@dataclass(frozen=True, slots=True)
class RuntimeBootstrapPhases:
    """Resolved runtime bootstrap phase outputs passed into runner construction."""

    registry: PipelineRegistry
    configs_root: Path
    factory_wiring: wiring.RunnerFactoryWiring
    input_wiring: wiring.RunnerInputWiring

    @property
    def wiring(self) -> wiring.RunnerBuilderWiring:
        """Return the canonical aggregate runner wiring bundle."""

        return wiring.RunnerBuilderWiring(self.factory_wiring, self.input_wiring)


def assemble_runtime_bootstrap_phases(
    *,
    registry: PipelineRegistry,
    configs_root: Path,
    factory_wiring: wiring.RunnerFactoryWiring,
    input_wiring: wiring.RunnerInputWiring,
) -> RuntimeBootstrapPhases:
    """Build the typed payload shared by runtime pipeline bootstrap seams."""
    return RuntimeBootstrapPhases(
        registry=registry,
        configs_root=configs_root,
        factory_wiring=factory_wiring,
        input_wiring=input_wiring,
    )


def assemble_vacuum_settings(
    *,
    cli_vacuum: CliVacuumSettings,
    yaml_maintenance: MaintenanceConfig,
) -> ResolvedVacuumSettings:
    """Merge CLI vacuum overrides with YAML defaults."""
    return _assemble_vacuum_settings(
        cli_vacuum=cli_vacuum, yaml_maintenance=yaml_maintenance
    )


def assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
) -> InputFilterConfig | None:
    """Assemble filter config from YAML plus run-context overrides."""
    return FilterConfigBuilder.build(
        yaml_filter=yaml_filter,
        cli_csv=ctx.input_filter.source_path if ctx.input_filter.enabled else None,
        cli_column=ctx.input_filter.column_name if ctx.input_filter.enabled else None,
        cli_field=ctx.input_filter.filter_field if ctx.input_filter.enabled else None,
        cli_fallback_column=(
            ctx.input_filter.fallback_column if ctx.input_filter.enabled else None
        ),
        test_mode=test_mode or ctx.ignore_yaml_filter,
        direct_filter_ids=ctx.input_filter.filter_ids,
        direct_fallback_mapping=ctx.input_filter.fallback_mapping,
        direct_multi_filter_ids=ctx.input_filter.multi_filter_ids,
        direct_valid_combinations=ctx.input_filter.valid_combinations,
    )


def assemble_cached_bronze_context(
    ctx: PipelineRunContext,
) -> CachedBronzeContext:
    """Return the cached-bronze context carried by the run context."""
    return ctx.cached_bronze


class _DebugExportOverrides(TypedDict, total=False):
    """Typed compatibility bundle for the three existing debug-export keywords."""

    debug_export_enabled: bool
    debug_export_formats: tuple[str, ...]
    debug_export_dir: str | None


_DEFAULT_PREFLIGHT_SETTINGS = PreflightRuntimeSettings()


def assemble_runtime_config(
    *,
    run_type: RunType,
    resume: bool,
    limit: int | None,
    query: str | None,
    dry_run: bool,
    heartbeat_interval: int,
    vacuum: ResolvedVacuumSettings,
    skip_gold: bool = False,
    workflow_id: str = "standalone",
    preflight: PreflightRuntimeSettings = _DEFAULT_PREFLIGHT_SETTINGS,
    health_check_mode: Literal["strict", "probe"] | None = None,
    **debug_export: Unpack[_DebugExportOverrides],
) -> RuntimeConfig:
    """Build runtime settings, preserving the existing debug-export keywords."""
    unsupported = debug_export.keys() - _DebugExportOverrides.__annotations__.keys()
    if unsupported:
        raise TypeError(f"Unexpected debug-export options: {sorted(unsupported)}")
    mode = health_check_mode
    return RuntimeConfig(
        run_type=run_type,
        resume=resume,
        limit=limit,
        heartbeat_interval=heartbeat_interval,
        query=query,
        dry_run=dry_run,
        vacuum_after_run=vacuum.enabled,
        vacuum_retention_days=vacuum.retention_days,
        skip_gold=skip_gold,
        debug_export_enabled=debug_export.get("debug_export_enabled", False),
        debug_export_formats=debug_export.get("debug_export_formats", ()),
        debug_export_dir=debug_export.get("debug_export_dir"),
        workflow_id=workflow_id,
        health_check_mode=mode if mode is not None else preflight.health_check_mode,
        strict_preflight=preflight.strict_preflight,
        silver_filter_compatibility_mode=resolve_silver_filter_compatibility_mode(),
    )
