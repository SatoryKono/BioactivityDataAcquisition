"""Pure assembly functions for pipeline bootstrap.

Contains pure, testable functions for assembling configuration objects
during pipeline bootstrap. These functions:
- Accept only data (no I/O, no settings loading, no DI)
- Return data (configuration objects or values)
- Are deterministic and side-effect free

This module reduces cognitive load in bootstrap_pipeline_runner by
extracting configuration assembly logic into discrete, testable units.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.runtime_builders.inputs_resolver import ResolvedVacuumSettings
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.types import RunType

if TYPE_CHECKING:
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
    "assemble_cached_bronze_context",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
]


def assemble_vacuum_settings(
    *,
    cli_vacuum: CliVacuumSettings,
    yaml_maintenance: MaintenanceConfig,
) -> ResolvedVacuumSettings:
    """Assemble effective vacuum settings from CLI overrides and YAML config.

    Implements tri-state merge logic:
    - CLI `enabled=None` → use YAML `auto_vacuum`
    - CLI `enabled=True/False` → explicit CLI override takes precedence

    Retention days follow same pattern: CLI override if vacuum explicitly enabled,
    otherwise YAML default.

    Args:
        cli_vacuum: Vacuum configuration from CLI (VacuumSettings with tri-state enabled).
        yaml_maintenance: Maintenance configuration from pipeline YAML.

    Returns:
        ResolvedVacuumSettings with resolved enabled flag and retention days.

    Example:
        >>> from bioetl.domain.context import VacuumSettings
        >>> # CLI doesn't override -> use YAML
        >>> cli = VacuumSettings(enabled=None, retention_days=7)
        >>> yaml = MaintenanceConfig(auto_vacuum=True, vacuum_retention_days=14)
        >>> result = assemble_vacuum_settings(cli_vacuum=cli, yaml_maintenance=yaml)
        >>> result.enabled
        True
        >>> result.retention_days
        14

        >>> # CLI explicitly overrides -> use CLI values
        >>> cli = VacuumSettings(enabled=False, retention_days=3)
        >>> result = assemble_vacuum_settings(cli_vacuum=cli, yaml_maintenance=yaml)
        >>> result.enabled
        False
        >>> result.retention_days
        3
    """
    # CLI explicit override takes precedence
    if cli_vacuum.enabled is not None:
        return ResolvedVacuumSettings(
            enabled=cli_vacuum.enabled,
            retention_days=cli_vacuum.retention_days,
        )

    # No CLI override -> use YAML defaults
    return ResolvedVacuumSettings(
        enabled=yaml_maintenance.auto_vacuum,
        retention_days=yaml_maintenance.vacuum_retention_days,
    )


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
    health_check_mode: Literal["strict", "probe"] = "strict",
) -> RuntimeConfig:
    """Assemble RuntimeConfig from resolved parameters.

    Creates an immutable RuntimeConfig value object from pre-resolved
    parameters. This function is pure and does not perform any I/O.

    Args:
        run_type: Type of pipeline run (incremental, backfill, rebuild).
        resume: Whether to resume from last checkpoint.
        limit: Optional record limit for the run.
        query: Optional query string for filtering.
        dry_run: Whether this is a dry run (no writes).
        heartbeat_interval: Interval in seconds for lock heartbeat.
        vacuum: Resolved vacuum settings.
        skip_gold: If True, Gold layer writes are skipped for this run.
        health_check_mode: Health check enforcement mode; 'strict' raises on
            failure, 'probe' logs and continues.

    Returns:
        Immutable RuntimeConfig instance.

    Example:
        >>> from bioetl.domain.types import RunType
        >>> vacuum = VacuumSettings(enabled=True, retention_days=7)
        >>> config = assemble_runtime_config(
        ...     run_type=RunType.INCREMENTAL,
        ...     resume=False,
        ...     limit=100,
        ...     query=None,
        ...     dry_run=False,
        ...     heartbeat_interval=30,
        ...     vacuum=vacuum,
        ... )
        >>> config.run_type
        <RunType.INCREMENTAL: 'incremental'>
        >>> config.vacuum_after_run
        True
    """
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
        health_check_mode=health_check_mode,
    )


def assemble_filter_config(
    *,
    yaml_filter: YamlInputFilter,
    ctx: PipelineRunContext,
    test_mode: bool,
) -> InputFilterConfig | None:
    """Assemble filter configuration from YAML and CLI context.

    Delegates to FilterConfigBuilder with parameters extracted from context.
    This wrapper provides a cleaner interface and makes the filter assembly
    logic explicit in the bootstrap pipeline.

    Priority (highest to lowest):
    1. direct_filter_ids from context (for composite mode)
    2. CLI input_filter (if enabled)
    3. YAML input_filter (disabled in test_mode or ignore_yaml_filter mode)

    Args:
        yaml_filter: Filter configuration from pipeline YAML.
        ctx: Pipeline run context containing CLI filter settings.
        test_mode: If True, YAML-based filters are disabled.

    Returns:
        Configured InputFilterConfig or None if filtering is disabled.

    Example:
        >>> # When CLI filter is enabled
        >>> result = assemble_filter_config(
        ...     yaml_filter=yaml_config.input_filter,
        ...     ctx=context,
        ...     test_mode=False,
        ... )
    """
    # Determine effective test_mode (includes ignore_yaml_filter from composite mode)
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
    """Assemble CachedBronzeContext from PipelineRunContext.

    Extracts cached bronze settings from the run context. The context
    is already populated from CLI options via RunOptions.

    Args:
        ctx: Pipeline run context with cached_bronze settings.

    Returns:
        CachedBronzeContext - either disabled or enabled with path/date.

    Example:
        >>> # When cached bronze is not requested
        >>> ctx = PipelineRunContext(
        ...     pipeline_name="chembl_activity",
        ...     run_id=uuid4(),
        ...     run_type=RunType.INCREMENTAL,
        ... )
        >>> result = assemble_cached_bronze_context(ctx)
        >>> result.enabled
        False

        >>> # When cached bronze is requested
        >>> ctx = PipelineRunContext(
        ...     pipeline_name="chembl_activity",
        ...     run_id=uuid4(),
        ...     run_type=RunType.INCREMENTAL,
        ...     cached_bronze=CachedBronzeContext.from_options(
        ...         path="/data/output/bronze/chembl/activity",
        ...         date="2026-01-20"
        ...     ),
        ... )
        >>> result = assemble_cached_bronze_context(ctx)
        >>> result.enabled
        True
    """
    return ctx.cached_bronze
