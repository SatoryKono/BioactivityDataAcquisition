"""Pipeline execution entrypoints.

Core functions for building, configuring, and running ETL pipelines.
Split from entrypoints.py per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
from bioetl.composition.bootstrap import (
    bootstrap_pipeline_runner,
    maybe_start_metrics_server,
)
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.providers.registration import register_all_providers
from bioetl.domain.context import (
    CachedBronzeContext,
    InputFilterContext,
    PipelineRunContext,
    VacuumConfig,
)
from bioetl.domain.types import ExecutionContext, RunID, RunType
from bioetl.infrastructure.config import get_settings

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner


def push_metrics_to_gateway(
    job: str = "bioetl",
) -> bool:
    """Push current metrics to Prometheus Pushgateway.

    Reads gateway URL from settings (BIOETL_PUSHGATEWAY_URL) and delegates
    to the infrastructure layer.

    Args:
        job: Job label for pushed metrics.

    Returns:
        True if push succeeded, False otherwise.
    """
    from bioetl.infrastructure.observability.server import (
        push_metrics_to_gateway as _push,
    )

    settings = get_settings()
    gateway = getattr(settings, "pushgateway_url", None) or "localhost:9091"
    return _push(gateway=gateway, job=job)


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
    return maybe_start_metrics_server(settings)


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


def _ensure_registrations() -> None:
    """Ensure all providers and pipelines are registered.

    This is idempotent and safe to call multiple times.
    """
    register_all_providers()
    register_all_pipelines()


def build_pipeline_context(name: str, options: RunOptions) -> PipelineRunContext:
    """Build a PipelineRunContext from user-facing options.

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Returns:
        PipelineRunContext ready for bootstrap_pipeline_runner.
    """
    # Build InputFilterContext from CLI options
    # Priority: multi_filter_ids > filter_ids > input_csv > disabled
    # - multi_filter_ids: Multi-field AND filtering (composite dependencies)
    # - filter_ids: Direct IDs for composite mode (no CSV file needed)
    # - input_csv: CSV file path, column_name/filter_field from YAML defaults
    if options.multi_filter_ids:
        # Multi-field filtering mode (composite dependencies with AND logic)
        input_filter = InputFilterContext.from_multi_ids(
            multi_filter_ids=options.multi_filter_ids,
        )
    elif options.filter_ids:
        # Direct IDs mode (composite pipelines)
        input_filter = InputFilterContext.from_ids(
            filter_ids=options.filter_ids,
            filter_field=options.filter_field
            or "doi",  # Default to DOI for publications
            fallback_mapping=options.fallback_mapping,  # Title fallback for OpenAlex etc.
        )
    elif options.input_csv:
        # CSV-based filtering
        input_filter = InputFilterContext(
            enabled=True,
            source_path=options.input_csv,
            column_name=options.filter_column or "",
            filter_field=options.filter_field or "",
        )
    else:
        input_filter = InputFilterContext.disabled()

    # Build VacuumConfig from CLI options (None means use YAML default)
    # Note: VacuumConfig here only captures CLI overrides.
    # The final merge with YAML config happens in bootstrap_pipeline_runner.
    # Tri-state logic:
    #   - None: No CLI override, use YAML default
    #   - True: CLI explicitly enables vacuum (--vacuum)
    #   - False: CLI explicitly disables vacuum (--no-vacuum)
    vacuum = VacuumConfig(
        enabled=options.vacuum_after_run,  # Preserve None for tri-state
        retention_days=options.vacuum_retention_days or 7,
    )

    # Build CachedBronzeContext from CLI options
    if options.use_cached_bronze:
        cached_bronze = CachedBronzeContext.from_options(
            path=options.cached_bronze_path,
            date=options.cached_bronze_date,
        )
    else:
        cached_bronze = CachedBronzeContext.disabled()

    return PipelineRunContext(
        pipeline_name=name,
        run_id=cast(RunID, uuid4()),
        run_type=RunType(options.run_type),
        resume=options.resume,
        limit=options.limit,
        dry_run=options.dry_run,
        input_filter=input_filter,
        vacuum=vacuum,
        log_level=options.log_level,
        ignore_yaml_filter=options.ignore_yaml_filter,
        skip_gold=options.skip_gold,
        cached_bronze=cached_bronze,
        execution_context=ExecutionContext(options.execution_context),
    )


def create_pipeline_runner(name: str, options: RunOptions) -> PipelineRunner:
    """Create a pipeline runner for the given pipeline and options.

    This is the main entrypoint for pipeline execution. It handles:
    - Registration of providers and pipelines
    - Building the pipeline context
    - Bootstrapping the runner with all dependencies

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Returns:
        PipelineRunner ready for execution via runner.run().

    Raises:
        ValueError: If pipeline name is unknown or options are invalid.
        FileNotFoundError: If pipeline config file is missing.

    Example:
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> runner = create_pipeline_runner("chembl_activity", options)
        >>> await runner.run()
    """
    _ensure_registrations()
    ctx = build_pipeline_context(name, options)
    return bootstrap_pipeline_runner(ctx)


async def run_pipeline(name: str, options: RunOptions) -> RunResult:
    """Run a pipeline with the given options.

    Unified pipeline execution interface that creates a runner, executes the
    pipeline, and returns structured results. This is the recommended way to
    run pipelines programmatically from any orchestration layer.

    For lower-level control over execution (e.g., signal handling, custom
    logging), use create_pipeline_runner() directly.

    Args:
        name: Pipeline name (e.g., 'chembl_activity').
        options: User-facing run options.

    Returns:
        RunResult with execution metrics and status.

    Raises:
        ValueError: If pipeline name is unknown or options are invalid.
        FileNotFoundError: If pipeline config file is missing.

    Example:
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> result = await run_pipeline("chembl_activity", options)
        >>> if result.status == PipelineRunResult.SUCCESS:
        ...     logger.info("pipeline_success", records_silver=result.records_silver)
        >>> elif result.status == PipelineRunResult.SHUTDOWN:
        ...     logger.info("pipeline_shutdown", pipeline="chembl_activity")
        >>> else:
        ...     logger.error("pipeline_failed", error_message=result.error_message)
    """
    # Start metrics server if enabled (side-effect in entrypoint, not bootstrap)
    settings = get_settings()
    maybe_start_metrics_server(settings)

    started_at = datetime.now(tz=UTC)
    runner = create_pipeline_runner(name, options)

    # Extract run context for result
    run_id = str(runner._context.run_id)
    run_type = options.run_type

    status = PipelineRunResult.SUCCESS
    error_message: str | None = None
    error_type: str | None = None

    try:
        await runner.run()
    except PipelineShutdownError:
        status = PipelineRunResult.SHUTDOWN
    except Exception as e:
        status = PipelineRunResult.FAILED
        error_message = str(e)
        error_type = type(e).__name__

    completed_at = datetime.now(tz=UTC)

    # Extract metrics from executor (composition layer has access to internals)
    executor = runner._executor
    return RunResult(
        status=status,
        pipeline_name=name,
        run_id=run_id,
        run_type=run_type,
        records_fetched=executor.records_fetched,
        records_bronze=executor.records_bronze,
        records_silver=executor.records_silver,
        records_gold=executor.records_gold,
        records_quarantined=executor.records_quarantined,
        started_at=started_at,
        completed_at=completed_at,
        error_message=error_message,
        error_type=error_type,
    )
