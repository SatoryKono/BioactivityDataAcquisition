"""Pipeline execution entrypoints.

Core functions for building, configuring, and running ETL pipelines.
Split from entrypoints.py per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from bioetl.application.runtime_timestamps import (
    capture_runtime_timing_anchor,
    derive_completion_timestamp,
)
from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
from bioetl.composition import PipelineRegistry
from bioetl.composition.bootstrap import (
    bootstrap_pipeline_runner,
    maybe_start_metrics_server,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.factories.pipeline.runner import create_metrics_extractor
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.domain.context import (
    CachedBronzeContext,
    InputFilterContext,
    PipelineRunContext,
    VacuumSettings,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.types import ExecutionContext, RunID, RunType
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.domain.ports import ExecutionMetricsRunnerPort


__all__ = [
    "ArchiveOptions",
    "VacuumOptions",
    "build_pipeline_context",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "push_metrics_to_gateway",
    "run_pipeline",
]


def _ensure_registrations(registry: PipelineRegistry | None = None) -> None:
    """Ensure providers and pipelines are registered for shared entrypoints."""
    ensure_providers_loaded()
    if registry is None or not registry.list_pipelines():
        register_all_pipelines(registry=registry)


def _require_execution_metrics_runner(
    runner: object,
) -> ExecutionMetricsRunnerPort:
    """Validate that the created runner is runnable and metrics-readable."""
    from bioetl.domain.ports import ExecutionMetricsRunnerPort

    if not isinstance(runner, ExecutionMetricsRunnerPort):
        raise TypeError("Runner does not implement ExecutionMetricsRunnerPort")
    return runner


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    pipeline_name: str | None = None,
    run_type: str | None = None,
) -> bool:
    """Push current metrics to Prometheus Pushgateway via composition.

    Args:
        run_label: Run label for pushed metrics.
        pipeline_name: Pipeline name for grouping (e.g. "chembl_molecule").
        run_type: Optional run type for grouping (e.g. "incremental").

    Returns:
        True if push succeeded, False otherwise.
    """
    from bioetl.composition.observability_api import (
        push_metrics_to_gateway as _push,
    )

    return bool(
        _push(
            run_label=run_label,
            pipeline_name=pipeline_name,
            run_type=run_type,
        )
    )


def ensure_metrics_server_started() -> bool:
    """Ensure metrics server is started if enabled in settings.

    This function should be called at the start of pipeline execution
    to start the Prometheus HTTP server. It's idempotent - calling it
    multiple times is safe.

    Returns:
        True if server was started or already running, False if disabled.

    Example:
        >>> ensure_metrics_server_started()
        True  # Server started on configured port
    """
    settings = get_settings()
    return bool(maybe_start_metrics_server(settings))


@dataclass(frozen=True)
class VacuumOptions:
    """Options for vacuum operation.

    Attributes:
        retention_days: Minimum age of files to remove (days).
        dry_run: Preview mode showing what would be removed.
    """

    retention_days: int = 7
    dry_run: bool = False


@dataclass(frozen=True)
class ArchiveOptions:
    """Options for archive operation.

    Attributes:
        target_path: Destination path for archive.
        remove_source: Remove source table after archiving.
    """

    target_path: str
    remove_source: bool = False


def _build_input_filter_context(options: RunOptions) -> InputFilterContext:
    """Build input filter context from CLI options.

    Args:
        options: User-facing run options containing filter configuration.

    Returns:
        InputFilterContext configured for multi-field, single-field, or CSV filtering.
    """
    if options.multi_filter_ids:
        return InputFilterContext.from_multi_ids(
            multi_filter_ids=options.multi_filter_ids,
        )
    if options.filter_ids:
        return InputFilterContext.from_ids(
            filter_ids=options.filter_ids,
            filter_field=options.filter_field or "doi",
            fallback_mapping=options.fallback_mapping,
        )
    if options.input_csv:
        return InputFilterContext(
            enabled=True,
            source_path=options.input_csv,
            column_name=options.filter_column or "",
            filter_field=options.filter_field or "",
        )
    return InputFilterContext.disabled()


def _build_vacuum_config(options: RunOptions) -> VacuumSettings:
    """Build vacuum config from CLI overrides (preserving tri-state).

    Args:
        options: User-facing run options containing vacuum configuration.

    Returns:
        VacuumSettings with enabled flag and retention_days.
    """
    return VacuumSettings(
        enabled=options.vacuum_after_run,
        retention_days=options.vacuum_retention_days or 7,
    )


def _build_cached_bronze_context(options: RunOptions) -> CachedBronzeContext:
    """Build cached bronze context from CLI options.

    Args:
        options: User-facing run options containing cached bronze settings.

    Returns:
        CachedBronzeContext enabled with path/date, or disabled if not requested.
    """
    if options.use_cached_bronze:
        return CachedBronzeContext.from_options(
            path=options.cached_bronze_path,
            date=options.cached_bronze_date,
        )
    if options.exact_replay:
        raise ValueError(
            "exact replay currently requires --use-cached-bronze with snapshot-backed Bronze inputs"
        )
    return CachedBronzeContext.disabled()


def build_pipeline_context(name: str, options: RunOptions) -> PipelineRunContext:
    """Build a PipelineRunContext from user-facing options.

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Returns:
        PipelineRunContext ready for bootstrap_pipeline_runner.
    """
    clock = SystemClock()
    started_at, _ = capture_runtime_timing_anchor(clock=clock)
    return PipelineRunContext(
        pipeline_name=name,
        run_id=cast(RunID, uuid4()),
        run_type=RunType(options.run_type),
        started_at=started_at,
        resume=options.resume,
        limit=options.limit,
        dry_run=options.dry_run,
        input_filter=_build_input_filter_context(options),
        vacuum=_build_vacuum_config(options),
        log_level=options.log_level,
        ignore_yaml_filter=options.ignore_yaml_filter,
        skip_gold=options.skip_gold,
        cached_bronze=_build_cached_bronze_context(options),
        exact_replay=options.exact_replay,
        execution_context=ExecutionContext(options.execution_context),
    )


def create_pipeline_runner(
    name: str,
    options: RunOptions,
) -> ExecutionMetricsRunnerPort:
    """Create a pipeline runner for the given pipeline and options.

    This is the main entrypoint for pipeline execution. It handles:
    - Registration of providers and pipelines
    - Building the pipeline context
    - Bootstrapping the runner with all dependencies

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Returns:
        ExecutionMetricsRunnerPort ready for execution via runner.run().

    Raises:
        ValueError: If pipeline name is unknown or options are invalid.
        FileNotFoundError: If pipeline config file is missing.

    Example:
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> runner = create_pipeline_runner("chembl_activity", options)
        >>> await runner.run()
    """
    run_context = build_pipeline_context(name, options)
    return _require_execution_metrics_runner(bootstrap_pipeline_runner(run_context))


async def run_pipeline(name: str, options: RunOptions) -> RunResult:
    """Run pipeline end-to-end and return structured execution result.

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options controlling execution behaviour.

    Returns:
        RunResult with execution status, record counts, and timing information.
    """
    # Start metrics server if enabled (side-effect in entrypoint, not bootstrap)
    settings = get_settings()
    maybe_start_metrics_server(settings)

    clock = SystemClock()
    started_at, started_monotonic = capture_runtime_timing_anchor(
        started_at=clock.now(),
        clock=clock,
    )
    runner = _require_execution_metrics_runner(create_pipeline_runner(name, options))

    # Extract run context for result
    run_id = runner.run_id
    run_type = options.run_type

    status = PipelineRunResult.SUCCESS
    error_message: str | None = None
    error_type: str | None = None

    try:
        await runner.run()
    except PipelineShutdownError:
        status = PipelineRunResult.SHUTDOWN
    except (BioETLError, OSError, RuntimeError, ValueError, TypeError) as e:
        status = PipelineRunResult.FAILED
        error_message = str(e)
        error_type = type(e).__name__

    completed_at, _ = derive_completion_timestamp(
        started_at=started_at,
        started_monotonic=started_monotonic,
    )

    metrics = create_metrics_extractor().extract_metrics(runner)
    result = RunResult(
        status=status,
        pipeline_name=name,
        run_id=run_id,
        run_type=run_type,
        records_fetched=int(metrics.get("records_fetched", 0)),
        records_bronze=int(metrics.get("records_bronze", 0)),
        records_silver=int(metrics.get("records_silver", 0)),
        records_gold=int(metrics.get("records_gold", 0)),
        records_quarantined=int(metrics.get("records_quarantined", 0)),
        records_filtered_out=int(metrics.get("records_filtered_out", 0)),
        started_at=started_at,
        completed_at=completed_at,
        error_message=error_message,
        error_type=error_type,
    )
    if settings.observability.metrics_enabled:
        push_metrics_to_gateway(
            run_label="bioetl",
            pipeline_name=name,
            run_type=run_type,
        )
    return result
