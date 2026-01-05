"""Entrypoints for BioETL pipeline operations.

Provides high-level functions for running pipelines and managing resources.
These entrypoints are designed to be used by CLI, REST APIs, or any other
orchestration layer without direct dependency on bootstrap functions.

This module provides the unified pipeline execution interface (REQ-ARCH-041).
Any orchestration layer should use these entrypoints instead of bootstrap.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

# Re-export canonical DTO classes from application.services (H1 refactoring)
# These are the single source of truth for pipeline execution interfaces.
from bioetl.application.services import RunOptions, RunResult, RunStatus

__all__ = [
    # Configuration
    "load_pipeline_config",
    # Option classes (re-exported from application.services)
    "RunOptions",
    "VacuumOptions",
    "ArchiveOptions",
    # Result classes (re-exported from application.services)
    "RunResult",
    "RunStatus",
    # Pipeline operations
    "build_pipeline_context",
    "create_pipeline_runner",
    "run_pipeline",
    # Resource management (managers - legacy)
    "get_quarantine_manager",
    "get_checkpoint_manager",
    "get_lifecycle_service",
    # Resource management (services - new)
    "get_checkpoint_service",
    "get_config_service",
    "get_health_server_dependencies",
    "get_health_service",
    "get_lock_service",
    "get_metrics_service",
    "get_pipeline_runner_service",
    "get_quarantine_service",
    "get_quarantine_store",
    "get_bronze_cleanup_service",
    "get_vacuum_service",
    # Maintenance operations
    "vacuum_table",
    "archive_table",
    "preview_cleanup",
    "cleanup_bronze",
    # Inspection
    "inspect_quarantine",
    "list_checkpoints",
]

from bioetl.composition._bootstrap import (
    HealthServerDependencies,
    bootstrap_bronze_cleanup_service,
    bootstrap_checkpoint_service,
    bootstrap_config_service,
    bootstrap_health_server_dependencies,
    bootstrap_health_service,
    bootstrap_lock_service,
    bootstrap_metrics_service,
    bootstrap_pipeline_runner_service,
    bootstrap_quarantine,
    bootstrap_quarantine_service,
    bootstrap_vacuum_service,
)
from bioetl.composition.bootstrap import (
    bootstrap_checkpoint_manager,
    bootstrap_cleanup,
    bootstrap_lifecycle_service,
    bootstrap_pipeline,
    bootstrap_quarantine_manager,
    load_pipeline_config,
)
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.providers.registration import register_all_providers
from bioetl.domain.context import InputFilterContext, PipelineRunContext, VacuumConfig
from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.cleanup_service import CleanupPreview
    from bioetl.application.core.quarantine_manager import QuarantineManager
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services import (
        BronzeCleanupService,
        CheckpointService,
        CleanupResult,
        ConfigService,
        HealthService,
        MetricsService,
        PipelineRunnerService,
        QuarantineService,
        VacuumService,
    )
    from bioetl.application.services.lock_service import LockService
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.ports import QuarantinePort


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
        PipelineRunContext ready for bootstrap_pipeline.
    """
    # Build InputFilterContext from CLI options
    # Allow partial CLI params - FilterConfigBuilder will merge with YAML defaults
    # If only input_csv is provided, column_name and filter_field come from YAML
    if options.input_csv:
        input_filter = InputFilterContext(
            enabled=True,
            source_path=options.input_csv,
            column_name=options.filter_column or "",  # Empty = use YAML default
            filter_field=options.filter_field or "",  # Empty = use YAML default
        )
    else:
        input_filter = InputFilterContext.disabled()

    # Build VacuumConfig from CLI options (None means use YAML default)
    # Note: VacuumConfig here only captures CLI overrides.
    # The final merge with YAML config happens in bootstrap_pipeline.
    # Tri-state logic:
    #   - None: No CLI override, use YAML default
    #   - True: CLI explicitly enables vacuum (--vacuum)
    #   - False: CLI explicitly disables vacuum (--no-vacuum)
    vacuum = VacuumConfig(
        enabled=options.vacuum_after_run,  # Preserve None for tri-state
        retention_days=options.vacuum_retention_days or 7,
    )

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
    return bootstrap_pipeline(ctx)


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
        >>> if result.status == RunStatus.SUCCESS:
        ...     logger.info("pipeline_success", records_silver=result.records_silver)
        >>> elif result.status == RunStatus.SHUTDOWN:
        ...     logger.info("pipeline_shutdown", pipeline="chembl_activity")
        >>> else:
        ...     logger.error("pipeline_failed", error_message=result.error_message)
    """
    from bioetl.application.core.shutdown import PipelineShutdownError

    started_at = datetime.now(tz=UTC)
    runner = create_pipeline_runner(name, options)

    # Extract run context for result
    run_id = str(runner._context.run_id)
    run_type = options.run_type

    status = RunStatus.SUCCESS
    error_message: str | None = None
    error_type: str | None = None

    try:
        await runner.run()
    except PipelineShutdownError:
        status = RunStatus.SHUTDOWN
    except Exception as e:
        status = RunStatus.FAILED
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


def get_quarantine_manager(pipeline: str) -> QuarantineManager:
    """Get a quarantine manager for the given pipeline.

    Used for inspecting and managing quarantined (failed) records.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        QuarantineManager instance for the pipeline.

    Example:
        >>> manager = get_quarantine_manager("chembl_activity")
        >>> records = await manager.inspect(limit=100)
    """
    _ensure_registrations()
    return bootstrap_quarantine_manager(pipeline)


def get_checkpoint_manager(pipeline: str) -> CheckpointManager:
    """Get a checkpoint manager for the given pipeline.

    Used for listing, loading, and managing pipeline checkpoints.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        CheckpointManager instance for the pipeline.

    Example:
        >>> manager = get_checkpoint_manager("chembl_activity")
        >>> checkpoints = await manager.list_all()
    """
    _ensure_registrations()
    return bootstrap_checkpoint_manager(pipeline)


def get_lifecycle_service() -> MedallionLifecycleService:
    """Get the lifecycle service for maintenance operations.

    Used for vacuum and archive operations on Delta tables.

    Returns:
        MedallionLifecycleService instance.

    Example:
        >>> service = get_lifecycle_service()
        >>> removed = await service.vacuum("chembl.activity", retention_days=7)
    """
    _ensure_registrations()
    return bootstrap_lifecycle_service()


async def vacuum_table(table: str, options: VacuumOptions) -> int:
    """Vacuum a Delta table to reclaim storage space.

    Args:
        table: Table name in format "provider.entity" (e.g., 'chembl.activity').
        options: Vacuum options including retention and dry_run.

    Returns:
        Number of files removed (or would be removed in dry_run mode).

    Example:
        >>> options = VacuumOptions(retention_days=30, dry_run=True)
        >>> files_removed = await vacuum_table("chembl.activity", options)
    """
    service = get_lifecycle_service()
    result: int = await service.vacuum(
        table=table,
        retention_days=options.retention_days,
        dry_run=options.dry_run,
    )
    return result


async def archive_table(table: str, options: ArchiveOptions) -> int:
    """Archive a Delta table to cold storage.

    Args:
        table: Table name to archive.
        options: Archive options including target path and remove_source.

    Returns:
        Number of files archived.

    Example:
        >>> options = ArchiveOptions(target_path="/archive/chembl", remove_source=False)
        >>> files_archived = await archive_table("chembl.activity", options)
    """
    service = get_lifecycle_service()
    result: int = await service.archive(
        table=table,
        target_path=options.target_path,
        remove_source=options.remove_source,
    )
    return result


async def preview_cleanup(pipeline: str) -> CleanupPreview:
    """Preview what data would be cleared for a pipeline.

    Used for dry-run mode of rebuild/backfill operations.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        CleanupPreview with information about what would be cleared.

    Example:
        >>> preview = await preview_cleanup("chembl_activity")
        >>> preview.total_files  # Number of files to clear
        42
    """
    _ensure_registrations()
    config = load_pipeline_config(pipeline)
    cleanup_service = bootstrap_cleanup()
    return await cleanup_service.preview(
        silver_table=config.silver_table,
        gold_table=config.gold_table,
    )


async def inspect_quarantine(pipeline: str, limit: int = 100) -> list[dict[str, Any]]:
    """Inspect quarantined records for a pipeline.

    Convenience function for quick quarantine inspection.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').
        limit: Maximum number of records to return.

    Returns:
        List of quarantine record dictionaries.

    Example:
        >>> records = await inspect_quarantine("chembl_activity", limit=50)
        >>> [rec['error_code'] for rec in records]  # List of error codes
        ['DQ_MISSING_FIELD', 'DQ_INVALID_SMILES']
    """
    manager = get_quarantine_manager(pipeline)
    records: list[dict[str, Any]] = await manager.inspect(limit=limit)
    return records


async def list_checkpoints(pipeline: str) -> list[str]:
    """List all checkpoints for a pipeline.

    Convenience function for quick checkpoint listing.

    Args:
        pipeline: Pipeline name (e.g., 'chembl_activity').

    Returns:
        List of checkpoint identifiers.

    Example:
        >>> checkpoints = await list_checkpoints("chembl_activity")
        >>> checkpoints  # List of checkpoint identifiers
        ['checkpoint_2024_01_15', 'checkpoint_2024_01_16']
    """
    manager = get_checkpoint_manager(pipeline)
    checkpoints: list[str] = await manager.list_all()
    return checkpoints


# =============================================================================
# New Application Services (replacing direct infrastructure access)
# =============================================================================


def get_checkpoint_service() -> CheckpointService:
    """Get a checkpoint service for administrative operations.

    Used for listing, deleting, and inspecting checkpoints across all pipelines.
    This is the recommended way to manage checkpoints from CLI or other interfaces.

    Returns:
        CheckpointService instance.

    Example:
        >>> service = get_checkpoint_service()
        >>> checkpoints = await service.list_checkpoints()
        >>> for cp in checkpoints:
        ...     logger.info("checkpoint", pipeline=cp.pipeline_name, metadata=cp.metadata)
    """
    _ensure_registrations()
    return bootstrap_checkpoint_service()


def get_quarantine_service() -> QuarantineService:
    """Get a quarantine service for administrative operations.

    Used for inspecting, replaying, and purging quarantine records.
    This is the recommended way to manage quarantine from CLI or other interfaces.

    Returns:
        QuarantineService instance.

    Example:
        >>> service = get_quarantine_service()
        >>> records = await service.inspect("chembl_activity", limit=10)
        >>> for rec in records:
        ...     logger.info("quarantine_record", error_code=rec.error_code, payload=rec.payload)
    """
    _ensure_registrations()
    return bootstrap_quarantine_service()


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Get a bronze cleanup service for maintenance operations.

    Used for Bronze layer retention cleanup per RULES.md §2.1.
    This is the recommended way to manage Bronze cleanup from CLI.

    Returns:
        BronzeCleanupService instance.

    Example:
        >>> service = get_bronze_cleanup_service()
        >>> result = await service.cleanup(retention_days=90, dry_run=True)
        >>> logger.info("cleanup_preview", files_to_remove=result.files_removed)
    """
    _ensure_registrations()
    return bootstrap_bronze_cleanup_service()


def get_vacuum_service() -> VacuumService:
    """Get a vacuum service for batch vacuum operations.

    Used for vacuuming multiple Delta tables at once.
    This is the recommended way to vacuum tables from CLI.

    Returns:
        VacuumService instance.

    Example:
        >>> service = get_vacuum_service()
        >>> tables = service.collect_tables(layer="all")
        >>> result = await service.vacuum_all(tables, retention_days=7)
        >>> logger.info("vacuum_complete", files_removed=result.total_files_removed)
    """
    _ensure_registrations()
    return bootstrap_vacuum_service()


def get_lock_service() -> LockService:
    """Get a lock service for administrative lock operations.

    Used for releasing stale locks and checking lock status.
    This is the recommended way to manage locks from CLI.

    Note: Uses in-memory locking which only affects the current process.
    Lock operations are local to this process instance.

    Returns:
        LockService instance.

    Example:
        >>> service = get_lock_service()
        >>> released = await service.release_lock("chembl_activity", run_id)
        >>> logger.info("lock_released", pipeline="chembl_activity", released=released)
    """
    _ensure_registrations()
    return bootstrap_lock_service()


async def cleanup_bronze(
    retention_days: int = 90,
    dry_run: bool = False,
) -> CleanupResult:
    """Clean up old Bronze files based on retention policy.

    Convenience function for Bronze cleanup operations.
    Removes files older than the specified retention period.

    Args:
        retention_days: Files older than this will be removed (default: 90).
        dry_run: If True, only show what would be removed.

    Returns:
        CleanupResult with cleanup statistics.

    Example:
        >>> result = await cleanup_bronze(retention_days=90, dry_run=True)
        >>> logger.info("cleanup_preview", files_to_remove=result.files_removed)
    """
    service = get_bronze_cleanup_service()
    result: CleanupResult = await service.cleanup(
        retention_days=retention_days,
        dry_run=dry_run,
    )
    return result


def get_pipeline_runner_service() -> PipelineRunnerService:
    """Get a pipeline runner service for universal pipeline execution.

    This is the recommended way to run pipelines programmatically from
    any interface (CLI, REST API, Airflow, etc.). The service provides
    a clean, stateless API for pipeline execution.

    Returns:
        PipelineRunnerService instance ready for use.

    Example:
        >>> from bioetl.application.services import RunOptions
        >>> service = get_pipeline_runner_service()
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> result = await service.run("chembl_activity", options=options)
        >>> if result.is_success:
        ...     logger.info("pipeline_success", records_silver=result.records_silver)
    """
    _ensure_registrations()
    return bootstrap_pipeline_runner_service()


# =============================================================================
# Configuration and Health Services
# =============================================================================


def get_config_service() -> ConfigService:
    """Get a configuration service for accessing application configuration.

    Provides a clean interface for configuration access from CLI or other
    interfaces. Abstracts infrastructure configuration loading.

    Returns:
        ConfigService instance for configuration operations.

    Example:
        >>> service = get_config_service()
        >>> settings = service.get_settings()
        >>> logger.info("environment", env=settings.env)
        >>> config = service.load_pipeline_config("chembl_activity")
        >>> logger.info("pipeline", provider=config.provider)
    """
    _ensure_registrations()
    return bootstrap_config_service()


def get_health_service() -> HealthService:
    """Get a health service for checking provider health.

    Provides a clean interface for health checking from CLI or other
    interfaces. Abstracts data source factory and adapter creation.

    Returns:
        HealthService instance for health check operations.

    Example:
        >>> service = get_health_service()
        >>> summary = await service.check_providers()
        >>> if summary.all_healthy:
        ...     logger.info("All providers healthy")
        >>> else:
        ...     for name, result in summary.results.items():
        ...         if result.is_unhealthy:
        ...             logger.error("Provider unhealthy", provider=name, error=result.error)
    """
    _ensure_registrations()
    return bootstrap_health_service()


def get_health_server_dependencies() -> HealthServerDependencies:
    """Get dependencies for HealthServer via composition root.

    Returns HealthServerDependencies with PrometheusMetrics and
    ProviderHealthMonitor. HealthServer is created in interfaces layer.
    """
    _ensure_registrations()
    return bootstrap_health_server_dependencies()


def get_metrics_service() -> MetricsService:
    """Get a metrics service for managing the Prometheus metrics server.

    Provides a clean interface for metrics server management from CLI or
    other interfaces. Abstracts infrastructure metrics server operations.

    Returns:
        MetricsService instance for metrics server operations.

    Example:
        >>> service = get_metrics_service()
        >>> result = service.start(port=8000)
        >>> if result.success:
        ...     logger.info("Metrics server started", port=result.port)
        >>> status = service.get_status()
        >>> logger.info("Server status", running=status.running)
    """
    _ensure_registrations()
    return bootstrap_metrics_service()


def get_quarantine_store(pipeline: str) -> QuarantinePort:
    """Get a quarantine store (port) for direct quarantine operations.

    This provides direct access to the QuarantinePort for low-level
    quarantine operations. For most use cases, prefer get_quarantine_service()
    which provides a higher-level interface.

    Args:
        pipeline: Pipeline name (used for context, actual store is shared).

    Returns:
        QuarantinePort instance for quarantine operations.

    Example:
        >>> store = get_quarantine_store("chembl_activity")
        >>> records = await store.inspect("chembl_activity", limit=10)
    """
    _ensure_registrations()
    return bootstrap_quarantine()
