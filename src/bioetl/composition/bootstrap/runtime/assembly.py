"""Pure assembly helpers for pipeline bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.runtime_builders.inputs_runtime_models import (
    ResolvedVacuumSettings,
)
from bioetl.domain.context import CachedBronzeContext
from bioetl.composition.runtime_builders.runner_builder_wiring import (
    RunnerBuilderWiring,
)
from bioetl.composition.bootstrap.runtime.assembly_assemble_runtime_config import (
    assemble_runtime_config,
)

if TYPE_CHECKING:
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.composition.runtime_builders.runner_builder_wiring import (
        RunnerBuilderWiring,
        RunnerFactoryWiring,
        RunnerInputWiring,
    )
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
    factory_wiring: RunnerFactoryWiring
    input_wiring: RunnerInputWiring

    @property
    def wiring(self) -> RunnerBuilderWiring:
        """Return the canonical aggregate runner wiring bundle."""

        return RunnerBuilderWiring(
            factory=self.factory_wiring,
            inputs=self.input_wiring,
        )


def assemble_runtime_bootstrap_phases(
    *,
    registry: PipelineRegistry,
    configs_root: Path,
    factory_wiring: RunnerFactoryWiring,
    input_wiring: RunnerInputWiring,
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
    if cli_vacuum.enabled is not None:
        return ResolvedVacuumSettings(
            enabled=cli_vacuum.enabled,
            retention_days=cli_vacuum.retention_days,
        )

    return ResolvedVacuumSettings(
        enabled=yaml_maintenance.auto_vacuum,
        retention_days=yaml_maintenance.vacuum_retention_days,
    )


def assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
) -> InputFilterConfig | None:
    """Assemble filter config from YAML plus run-context overrides."""
    effective_test_mode = test_mode or ctx.ignore_yaml_filter

    return FilterConfigBuilder.build(
        yaml_filter=yaml_filter,
        cli_csv=ctx.input_filter.source_path if ctx.input_filter.enabled else None,
        cli_column=ctx.input_filter.column_name if ctx.input_filter.enabled else None,
        cli_field=ctx.input_filter.filter_field if ctx.input_filter.enabled else None,
        cli_fallback_column=(
            ctx.input_filter.fallback_column if ctx.input_filter.enabled else None
        ),
        test_mode=effective_test_mode,
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
