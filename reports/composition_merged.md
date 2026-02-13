================================================================================
File: __init__.py
Path: __init__.py
================================================================================
"""Composition Root for BioETL dependency injection.

This package contains the Composition Root - the single place where
all dependencies are composed and wired together according to the
Ports & Adapters architecture (RULES.md).

Components:
    bootstrap: Pipeline bootstrapping and factory functions.
    registry: Pipeline registry for dynamic pipeline discovery.
    builders: Builder classes for constructing pipelines.
    types: Type definitions for composition layer.
    observability: Observability setup (tracing, metrics, logging).
    entrypoints: CLI and API entrypoints.

The composition layer is the only layer allowed to import from
infrastructure and wire concrete implementations to domain ports.

See Also:
    docs/02-architecture/decisions/ADR-005-composition-layer.md
"""

================================================================================
File: _pipeline_execution.py
Path: _pipeline_execution.py
================================================================================
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
    bootstrap_pipeline,
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
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.config import get_settings

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner


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
        PipelineRunContext ready for bootstrap_pipeline.
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
    # The final merge with YAML config happens in bootstrap_pipeline.
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

================================================================================
File: _resource_management.py
Path: _resource_management.py
================================================================================
"""Resource management entrypoints.

Legacy managers, maintenance operations (vacuum, archive),
and inspection functions (quarantine, checkpoints).
Split from entrypoints.py per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.composition._pipeline_execution import (
    ArchiveOptions,
    VacuumOptions,
    _ensure_registrations,
)
from bioetl.composition.bootstrap import (
    bootstrap_checkpoint_manager,
    bootstrap_cleanup,
    bootstrap_lifecycle_service,
    bootstrap_quarantine_manager,
    load_pipeline_config,
)

if TYPE_CHECKING:
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.cleanup_service import CleanupPreview
    from bioetl.application.core.quarantine_manager import QuarantineManager
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
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

================================================================================
File: _services.py
Path: _services.py
================================================================================
"""Service factory entrypoints.

Application and infrastructure service getters for CLI and other interfaces.
Split from entrypoints.py per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition._pipeline_execution import _ensure_registrations
from bioetl.composition.bootstrap import (
    HealthServerDependencies,
    bootstrap_bronze_cleanup_service,
    bootstrap_checkpoint_service,
    bootstrap_config_service,
    bootstrap_export_service,
    bootstrap_health_server_dependencies,
    bootstrap_health_service,
    bootstrap_lock_service,
    bootstrap_metrics_service,
    bootstrap_pipeline_runner_service,
    bootstrap_quarantine,
    bootstrap_quarantine_service,
    bootstrap_vacuum_service,
)

if TYPE_CHECKING:
    from bioetl.application.services import (
        BronzeCleanupService,
        CheckpointService,
        CleanupResult,
        ConfigService,
        ExportService,
        HealthService,
        MetricsService,
        PipelineRunnerService,
        QuarantineService,
        VacuumService,
    )
    from bioetl.application.services.lock_service import LockService
    from bioetl.domain.ports import QuarantinePort


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


def get_export_service() -> ExportService:
    """Get an export service for exporting Delta Lake tables.

    Used for exporting Silver/Gold Delta tables to CSV, XLSX, and TSV formats.
    This is the recommended way to export tables from CLI.

    Returns:
        ExportService instance.

    Example:
        >>> service = get_export_service()
        >>> tables = service.list_tables(layer="silver")
        >>> result = await service.export("chembl.activity", layer="silver")
        >>> logger.info("export_complete", output=result.output_path)
    """
    _ensure_registrations()
    return bootstrap_export_service()


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

================================================================================
File: __init__.py
Path: bootstrap\__init__.py
================================================================================
"""Bootstrap package for BioETL Composition Root.

Provides modular bootstrap functions organized by context:

- **assembly**: Shared infrastructure components (ports, storage adapters)
  without side-effects. Used by both CLI and runtime.
- **cli**: Bootstrap functions for CLI-only commands (inspect, list, maintenance,
  admin operations). These use NoOp observability implementations.
- **runtime**: Bootstrap functions for actual pipeline execution (pipeline run,
  composite pipelines). These use full observability stack.

Import Rules:
- runtime MUST NOT import from cli
- cli MAY import from runtime (for runner access)
- Both MUST import shared code from assembly

All functions are re-exported here for backward compatibility with existing code.
"""

from __future__ import annotations

# =============================================================================
# Assembly (shared infrastructure without side-effects)
# =============================================================================
from bioetl.composition.bootstrap.assembly import (
    # Deprecated aliases
    bootstrap_checkpoint,
    # Canonical names
    bootstrap_checkpoint_port,
    bootstrap_quarantine,
    bootstrap_quarantine_port,
    bootstrap_storage,
    bootstrap_storage_adapter,
)

# =============================================================================
# CLI-specific services (NoOp observability, admin operations)
# =============================================================================
from bioetl.composition.bootstrap.cli import (
    HealthServerDependencies,
    bootstrap_bronze_cleanup_service,
    bootstrap_checkpoint_manager,
    bootstrap_checkpoint_service,
    # Deprecated alias
    bootstrap_cleanup,
    # Canonical name
    bootstrap_cleanup_service,
    bootstrap_config_service,
    bootstrap_export_service,
    bootstrap_health_server_dependencies,
    bootstrap_health_service,
    bootstrap_lifecycle_service,
    bootstrap_lock_service,
    bootstrap_metrics_service,
    bootstrap_quarantine_manager,
    bootstrap_quarantine_service,
    bootstrap_vacuum_service,
)

# =============================================================================
# Runtime services (full observability, pipeline execution)
# =============================================================================
from bioetl.composition.bootstrap.runtime import (
    MetricsServerError,
    # Assembly (pure functions)
    VacuumSettings,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
    # Deprecated aliases
    bootstrap_composite_pipeline,
    # Canonical names
    bootstrap_composite_runner,
    bootstrap_dq_monitor,
    bootstrap_dq_monitor_port,
    bootstrap_logger,
    bootstrap_logger_port,
    bootstrap_metrics,
    bootstrap_metrics_port,
    bootstrap_observability,
    bootstrap_observability_bundle,
    bootstrap_pipeline,
    bootstrap_pipeline_runner,
    bootstrap_pipeline_runner_service,
    bootstrap_tracer,
    bootstrap_tracer_port,
    load_composite_config,
    maybe_start_metrics_server,
    start_metrics_server,
    validate_observability_preflight,
)

# =============================================================================
# Config loader (re-exported for convenience)
# =============================================================================
from bioetl.infrastructure.config import load_pipeline_config

__all__ = [
    # CLI services
    "HealthServerDependencies",
    # Runtime services
    "MetricsServerError",
    # Runtime assembly (pure functions)
    "VacuumSettings",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
    "bootstrap_bronze_cleanup_service",
    # Assembly (deprecated aliases)
    "bootstrap_checkpoint",
    # Checkpoint & Quarantine managers/services
    "bootstrap_checkpoint_manager",
    # Assembly (canonical)
    "bootstrap_checkpoint_port",
    "bootstrap_checkpoint_service",
    # CLI cleanup (deprecated alias)
    "bootstrap_cleanup",
    # CLI cleanup (canonical)
    "bootstrap_cleanup_service",
    # Runtime composite (deprecated alias)
    "bootstrap_composite_pipeline",
    # Runtime composite (canonical)
    "bootstrap_composite_runner",
    "bootstrap_config_service",
    # Runtime observability (deprecated aliases)
    "bootstrap_dq_monitor",
    # Runtime observability (canonical)
    "bootstrap_dq_monitor_port",
    "bootstrap_export_service",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
    "bootstrap_lifecycle_service",
    "bootstrap_lock_service",
    "bootstrap_logger",
    "bootstrap_logger_port",
    "bootstrap_metrics",
    "bootstrap_metrics_port",
    "bootstrap_metrics_service",
    "bootstrap_observability",
    "bootstrap_observability_bundle",
    # Runtime pipeline (deprecated alias)
    "bootstrap_pipeline",
    # Runtime pipeline (canonical)
    "bootstrap_pipeline_runner",
    "bootstrap_pipeline_runner_service",
    "bootstrap_quarantine",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_port",
    "bootstrap_quarantine_service",
    "bootstrap_storage",
    "bootstrap_storage_adapter",
    "bootstrap_tracer",
    "bootstrap_tracer_port",
    "bootstrap_vacuum_service",
    "load_composite_config",
    # Config loader
    "load_pipeline_config",
    "maybe_start_metrics_server",
    "start_metrics_server",
    "validate_observability_preflight",
]

================================================================================
File: __init__.py
Path: bootstrap\assembly\__init__.py
================================================================================
"""Assembly module for shared bootstrap infrastructure.

Contains bootstrap functions for infrastructure components that are used by
both CLI and runtime contexts. These functions have no side-effects and
create pure infrastructure adapters.

Components:
- checkpoint: Checkpoint and quarantine port creation
- storage: Storage adapter assembly for I/O operations

Note:
    This module should NOT contain any NoOp implementations or CLI-specific
    logic. It provides neutral building blocks for higher-level bootstrap.
"""

from __future__ import annotations

from bioetl.composition.bootstrap.assembly.checkpoint import (
    # Deprecated aliases
    bootstrap_checkpoint,
    # Canonical names
    bootstrap_checkpoint_port,
    bootstrap_quarantine,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.assembly.storage import (
    # Deprecated alias
    bootstrap_storage,
    # Canonical name
    bootstrap_storage_adapter,
)

__all__ = [
    # Deprecated aliases (backward compatibility)
    "bootstrap_checkpoint",
    # Canonical names (use these)
    "bootstrap_checkpoint_port",
    "bootstrap_quarantine",
    "bootstrap_quarantine_port",
    "bootstrap_storage",
    "bootstrap_storage_adapter",
]

================================================================================
File: checkpoint.py
Path: bootstrap\assembly\checkpoint.py
================================================================================
"""Bootstrap functions for checkpoint and quarantine ports.

Provides basic port creation for checkpoint and quarantine infrastructure.
These are low-level building blocks used by both CLI and runtime.

Note:
    Higher-level managers and services are created in cli/ module
    since they require additional context (pipeline_name, run_id, etc.)
    and use NoOp observability for CLI operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.quarantine import UnifiedQuarantine

if TYPE_CHECKING:
    from bioetl.domain.ports import CheckpointPort, QuarantinePort

__all__ = [
    # Deprecated aliases (backward compatibility)
    "bootstrap_checkpoint",
    # Canonical names (use these)
    "bootstrap_checkpoint_port",
    "bootstrap_quarantine",
    "bootstrap_quarantine_port",
]


def bootstrap_quarantine_port() -> QuarantinePort:
    """Create a quarantine port implementation for record quarantine storage.

    Creates a UnifiedQuarantine adapter using centralized quarantine_path
    from settings (data_dir/quarantine) for unified quarantine storage
    independent of entity paths.

    Layer: Returns domain port implementation (QuarantinePort).

    Returns:
        QuarantinePort implementation for quarantine operations.
    """
    settings = get_settings()
    return UnifiedQuarantine(base_path=str(settings.quarantine_path))


def bootstrap_quarantine() -> QuarantinePort:
    """Bootstrap the quarantine port for record quarantine storage.

    .. deprecated::
        Use :func:`bootstrap_quarantine_port` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Returns:
        QuarantinePort implementation for quarantine operations.
    """
    return bootstrap_quarantine_port()


def bootstrap_checkpoint_port(pipeline_name: str) -> CheckpointPort:
    """Create a checkpoint port implementation for pipeline state persistence.

    Creates a LocalCheckpoint adapter for the specified pipeline using
    the checkpoint_path from settings.

    Layer: Returns domain port implementation (CheckpointPort).

    Args:
        pipeline_name: Name of the pipeline for checkpoint scoping.

    Returns:
        CheckpointPort implementation for checkpoint operations.
    """
    settings = get_settings()
    return LocalCheckpoint(
        base_path=settings.checkpoint_path,
        pipeline_name=pipeline_name,
    )


def bootstrap_checkpoint(pipeline_name: str) -> CheckpointPort:
    """Bootstrap the checkpoint port for pipeline state persistence.

    .. deprecated::
        Use :func:`bootstrap_checkpoint_port` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        pipeline_name: Name of the pipeline for checkpoint scoping.

    Returns:
        CheckpointPort implementation for checkpoint operations.
    """
    return bootstrap_checkpoint_port(pipeline_name=pipeline_name)

================================================================================
File: storage.py
Path: bootstrap\assembly\storage.py
================================================================================
"""Bootstrap functions for storage adapter assembly.

Provides storage adapter creation for both CLI preview operations and
composite pipeline execution. This is a shared building block.

Note:
    This function uses NoOpLogger internally as observability is not
    required for storage adapter assembly. The actual observability
    is provided at a higher level (BatchWriter, RecordProcessor).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from bioetl.composition.factories.storage import StorageAdapter
from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
from bioetl.domain.ports import NoOpMetrics, NoOpTracing
from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = [
    # Deprecated alias (backward compatibility)
    "bootstrap_storage",
    # Canonical name (use this)
    "bootstrap_storage_adapter",
]


def bootstrap_storage_adapter(*, enable_csv_export: bool = False) -> StorageAdapter:
    """Create a storage adapter for CLI and composite pipeline operations.

    Creates a StorageAdapter suitable for preview operations and composite
    pipelines. CSV export is disabled by default for read-only inspection
    but can be enabled for composite pipelines that need CSV output.

    Uses NoOpLogger since this is for CLI preview operations without observability.

    Layer: Returns infrastructure adapter (StorageAdapter) containing
    Bronze, Silver, and Gold writers.

    Note:
        Lock validation is performed at Application layer (BatchWriter)
        per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.

    Args:
        enable_csv_export: If True, creates CsvExporters for Silver and Gold
            layers. Used by composite pipelines that need CSV output.

    Returns:
        StorageAdapter configured for the current environment.
    """
    settings = get_settings()
    noop_logger = NoOpLogger()
    noop_metrics = NoOpMetrics()
    noop_tracing = NoOpTracing()

    # ADR-025: Use data/output/ hierarchy for consistency with pipeline configs
    output_dir = Path(settings.data_dir) / "output"

    # Create metadata services for composite pipelines
    metadata_writer = MetadataWriter(logger=noop_logger)
    run_context = RunContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
        pipeline_name="composite",
        provider="composite",
        entity="merged",
    )
    metadata_coordinator = MetadataCoordinator(run_context=run_context)

    # Create CSV exporters if enabled (for composite pipelines)
    silver_csv_exporter = None
    gold_csv_exporter = None
    if enable_csv_export:
        silver_csv_exporter = CsvExporter(
            base_path=str(output_dir / "silver"),
            logger=noop_logger,
        )
        gold_csv_exporter = CsvExporter(
            base_path=str(output_dir / "gold"),
            logger=noop_logger,
        )

    return StorageAdapter(
        bronze_writer=BronzeWriter(
            base_path=output_dir / "bronze",  # data/output/bronze
            logger=noop_logger,
            metrics=noop_metrics,
            tracing=noop_tracing,
            save_json=False,
            json_path=None,
        ),
        silver_writer=SilverWriter(
            base_path=output_dir / "silver",  # data/output/silver
            logger=noop_logger,
            tracing=noop_tracing,
            csv_exporter=silver_csv_exporter,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
        ),
        gold_writer=GoldWriter(
            base_path=output_dir / "gold",  # data/output/gold
            logger=noop_logger,
            tracing=noop_tracing,
            csv_exporter=gold_csv_exporter,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
        ),
    )


def bootstrap_storage(*, enable_csv_export: bool = False) -> StorageAdapter:
    """Bootstrap a storage adapter for CLI and composite pipeline operations.

    .. deprecated::
        Use :func:`bootstrap_storage_adapter` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        enable_csv_export: If True, creates CsvExporters for Silver and Gold
            layers. Used by composite pipelines that need CSV output.

    Returns:
        StorageAdapter configured for the current environment.
    """
    return bootstrap_storage_adapter(enable_csv_export=enable_csv_export)

================================================================================
File: __init__.py
Path: bootstrap\cli\__init__.py
================================================================================
"""CLI bootstrap module for administrative operations.

Contains bootstrap functions for CLI-only commands:
- Inspection: quarantine inspect, checkpoint list
- Maintenance: vacuum, archive, bronze cleanup
- Admin: lock management, health checks, metrics server
- Configuration: settings access, pipeline config loading

These functions use NoOp observability implementations since CLI operations
don't require full runtime observability (no run_id, no metrics collection).

IMPORTANT: This module MUST NOT be imported by bootstrap/runtime/.
CLI may import from runtime for runner access, but not vice versa.

Components:
- checkpoint: Manager and service bootstrap for checkpoint operations
- config: ConfigService bootstrap
- health: HealthService and health server dependencies
- lock: LockService bootstrap
- metrics: MetricsService for server management (not metrics collection)
- storage: Maintenance services (cleanup, vacuum, export, lifecycle)
"""

from __future__ import annotations

from bioetl.composition.bootstrap.cli.checkpoint import (
    bootstrap_checkpoint_manager,
    bootstrap_checkpoint_service,
    bootstrap_quarantine_manager,
    bootstrap_quarantine_service,
)
from bioetl.composition.bootstrap.cli.config import bootstrap_config_service
from bioetl.composition.bootstrap.cli.health import (
    HealthServerDependencies,
    bootstrap_health_server_dependencies,
    bootstrap_health_service,
)
from bioetl.composition.bootstrap.cli.lock import bootstrap_lock_service
from bioetl.composition.bootstrap.cli.metrics import bootstrap_metrics_service
from bioetl.composition.bootstrap.cli.noop import (
    create_noop_logger,
    create_noop_metrics,
    create_noop_observability_bundle,
    create_noop_tracing,
)
from bioetl.composition.bootstrap.cli.storage import (
    bootstrap_bronze_cleanup_service,
    # Deprecated alias
    bootstrap_cleanup,
    # Canonical name
    bootstrap_cleanup_service,
    bootstrap_export_service,
    bootstrap_lifecycle_service,
    bootstrap_vacuum_service,
)

__all__ = [
    # Health
    "HealthServerDependencies",
    # Storage & Maintenance (canonical)
    "bootstrap_bronze_cleanup_service",
    # Checkpoint & Quarantine
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    # Storage & Maintenance (deprecated alias)
    "bootstrap_cleanup",
    "bootstrap_cleanup_service",
    # Config
    "bootstrap_config_service",
    "bootstrap_export_service",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
    "bootstrap_lifecycle_service",
    # Lock
    "bootstrap_lock_service",
    # Metrics
    "bootstrap_metrics_service",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_service",
    "bootstrap_vacuum_service",
    # NoOp factories (centralized)
    "create_noop_logger",
    "create_noop_metrics",
    "create_noop_observability_bundle",
    "create_noop_tracing",
]

================================================================================
File: checkpoint.py
Path: bootstrap\cli\checkpoint.py
================================================================================
"""Bootstrap functions for checkpoint and quarantine CLI operations.

Contains bootstrap functions for checkpoint manager, checkpoint service,
quarantine manager, and quarantine service. Used for CLI inspection
and administrative operations.

Note:
    These functions use NoOp observability since CLI operations don't
    require full runtime observability.
"""

from __future__ import annotations

from uuid import uuid4

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.services import CheckpointService, QuarantineService
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_checkpoint_port,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.domain.types import RunID
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.config import get_settings

__all__ = [
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_service",
]


def bootstrap_quarantine_manager(pipeline_name: str) -> QuarantineManager:
    """Bootstrap QuarantineManager for CLI inspection operations.

    Creates a QuarantineManager for quarantine inspection and reporting.
    Used by CLI for `quarantine inspect` and similar commands.

    Args:
        pipeline_name: Name of the pipeline to inspect.

    Returns:
        QuarantineManager configured for the specified pipeline.
    """
    quarantine_port = bootstrap_quarantine_port()
    return QuarantineManager(
        quarantine_port=quarantine_port,
        pipeline_name=pipeline_name,
    )


def bootstrap_checkpoint_manager(pipeline_name: str) -> CheckpointManager:
    """Bootstrap CheckpointManager for CLI inspection operations.

    Creates a minimal CheckpointManager for checkpoint listing and inspection.
    Uses NoOpLogger and dummy run_id since CLI operations don't need full
    pipeline execution context.

    Args:
        pipeline_name: Name of the pipeline (used for context, may be ignored
            for operations like list_all).

    Returns:
        CheckpointManager configured for CLI inspection.
    """
    checkpoint_port = bootstrap_checkpoint_port(pipeline_name)
    noop_logger = create_noop_logger()

    return CheckpointManager(
        checkpoint_port=checkpoint_port,
        logger=noop_logger,
        pipeline_name=pipeline_name,
        run_id=RunID(uuid4()),  # Dummy run_id for CLI inspection
        resume=False,
    )


def bootstrap_checkpoint_service() -> CheckpointService:
    """Bootstrap CheckpointService for CLI administrative operations.

    Creates a CheckpointService for checkpoint listing, deletion, and inspection.
    Uses a generic checkpoint port that can list all pipelines.

    Returns:
        CheckpointService configured for CLI operations.
    """
    settings = get_settings()
    # Use empty pipeline name for global operations
    checkpoint_port = LocalCheckpoint(
        base_path=settings.checkpoint_path,
        pipeline_name="",
    )
    noop_logger = create_noop_logger()

    return CheckpointService(
        checkpoint_port=checkpoint_port,
        logger=noop_logger,
    )


def bootstrap_quarantine_service() -> QuarantineService:
    """Bootstrap QuarantineService for CLI administrative operations.

    Creates a QuarantineService for quarantine inspection, replay, and purge.

    Returns:
        QuarantineService configured for CLI operations.
    """
    quarantine_port = bootstrap_quarantine_port()
    noop_logger = create_noop_logger()

    return QuarantineService(
        quarantine_port=quarantine_port,
        logger=noop_logger,
    )

================================================================================
File: config.py
Path: bootstrap\cli\config.py
================================================================================
"""Bootstrap functions for configuration CLI operations.

Contains bootstrap functions for ConfigService.
Used primarily by CLI configuration operations.
"""

from __future__ import annotations

from bioetl.application.services import ConfigService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.registry import get_default_registry
from bioetl.infrastructure.config import (
    get_settings,
    load_pipeline_config,
    yaml_config_to_domain,
)

__all__ = ["bootstrap_config_service"]


def bootstrap_config_service() -> ConfigService:
    """Bootstrap ConfigService for CLI configuration operations.

    Creates a ConfigService for configuration access and validation.
    Wires up infrastructure dependencies for configuration loading.

    Returns:
        ConfigService configured for CLI operations.

    Example:
        >>> service = bootstrap_config_service()
        >>> settings = service.get_settings()
        >>> logger.info("environment", env=settings.env)
    """
    noop_logger = create_noop_logger()

    # Ensure pipelines are registered for list_pipelines()
    register_all_pipelines()

    return ConfigService(
        logger=noop_logger,
        _settings_loader=get_settings,
        _pipeline_config_loader=load_pipeline_config,
        _domain_config_mapper=yaml_config_to_domain,
        _registry_accessor=get_default_registry,
    )

================================================================================
File: health.py
Path: bootstrap\cli\health.py
================================================================================
"""Bootstrap functions for health CLI operations.

Contains bootstrap functions for HealthService and health server dependencies.
Used primarily by CLI health operations.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services import HealthService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.factories.data_source_factory import DataSourceFactory
from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.adapters.http.health_monitor import ProviderHealthMonitor
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics

__all__ = [
    "HealthServerDependencies",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
]


@dataclass(frozen=True, slots=True)
class HealthServerDependencies:
    """Dependencies for HealthServer, provided by composition layer.

    This dataclass allows composition to provide dependencies without
    importing from interfaces layer (which would violate layer rules).

    Attributes:
        health_monitor: ProviderHealthMonitor for health state tracking.
        metrics: MetricsPort for observability.
    """

    health_monitor: ProviderHealthMonitor
    metrics: MetricsPort


def bootstrap_health_service() -> HealthService:
    """Bootstrap HealthService for CLI health operations.

    Creates a HealthService for checking provider health.
    Wires up DataSourceFactory for adapter creation.

    Returns:
        HealthService configured for CLI operations.

    Example:
        >>> service = bootstrap_health_service()
        >>> summary = await service.check_providers()
        >>> if summary.all_healthy:
        ...     logger.info("All providers healthy")
    """
    noop_logger = create_noop_logger()

    return HealthService(
        logger=noop_logger,
        _factory=DataSourceFactory,
    )


def bootstrap_health_server_dependencies() -> HealthServerDependencies:
    """Bootstrap dependencies for HealthServer via DI.

    Creates and wires up:
    - PrometheusMetrics for observability
    - ProviderHealthMonitor for health state tracking

    The actual HealthServer is created in the interfaces layer
    to maintain proper layer separation (composition cannot import interfaces).

    Returns:
        HealthServerDependencies with metrics and health_monitor.

    Example:
        >>> deps = bootstrap_health_server_dependencies()
        >>> server = HealthServer(host="127.0.0.1", port=9090,
        ...                       health_monitor=deps.health_monitor)
    """
    # Create metrics port for health monitor
    metrics = PrometheusMetrics()

    # Create health monitor with injected metrics
    health_monitor = ProviderHealthMonitor(metrics=metrics)

    return HealthServerDependencies(
        health_monitor=health_monitor,
        metrics=metrics,
    )

================================================================================
File: lock.py
Path: bootstrap\cli\lock.py
================================================================================
"""Bootstrap functions for lock CLI operations.

Contains bootstrap functions for lock service used by CLI operations.
"""

from __future__ import annotations

from bioetl.application.services.lock_service import LockService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.infrastructure.locking.memory_lock import MemoryLock

__all__ = ["bootstrap_lock_service"]


def bootstrap_lock_service() -> LockService:
    """Bootstrap LockService for CLI lock management commands.

    Creates a LockService for administrative lock operations.
    Used by CLI for `lock release` and `lock list` commands.

    Note: Uses MemoryLock which is the in-process lock implementation.
    Lock operations only affect the current process. For distributed
    scenarios, a Redis-based implementation would be needed.

    Returns:
        LockService configured for the current environment.
    """
    lock_port = MemoryLock()
    noop_logger = create_noop_logger()

    return LockService(lock_port=lock_port, logger=noop_logger)

================================================================================
File: metrics.py
Path: bootstrap\cli\metrics.py
================================================================================
"""Bootstrap functions for metrics CLI operations.

Contains bootstrap functions for MetricsService.
Used for metrics server management from CLI (start, stop, status).

Note:
    This is for managing the metrics server, not for metrics collection.
    Runtime metrics collection uses bootstrap/runtime/observability.py.
"""

from __future__ import annotations

from bioetl.application.services.metrics_service import MetricsService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.infrastructure.observability.metrics_server_adapter import (
    MetricsServerAdapter,
)

__all__ = ["bootstrap_metrics_service"]


def bootstrap_metrics_service() -> MetricsService:
    """Bootstrap metrics service for administrative operations.

    Creates a MetricsService with infrastructure dependencies injected.
    Used by CLI and other interfaces for metrics server management.

    Returns:
        MetricsService instance ready for use.

    Example:
        >>> service = bootstrap_metrics_service()
        >>> result = service.start(port=8000)
        >>> # result.success is True if server started
    """
    logger = create_noop_logger()
    server = MetricsServerAdapter(logger=logger)

    return MetricsService(
        logger=logger,
        _server=server,
    )

================================================================================
File: noop.py
Path: bootstrap\cli\noop.py
================================================================================
"""Centralized NoOp dependency factory functions for CLI bootstrap.

Contains pure factory functions for creating NoOp implementations used by
CLI-specific bootstrap functions. These provide silent/null implementations
for observability dependencies when full observability is not needed.

Usage:
    # In CLI bootstrap modules
    from bioetl.composition.bootstrap.cli.noop import create_noop_logger

    logger = create_noop_logger()

Design Decisions:
    - Pure functions, not singletons or factory objects
    - Each call creates a new instance (no hidden state sharing)
    - CLI-specific: warn_on_use=False for metrics (intentional opt-out)
    - MUST NOT be imported by runtime code

Note:
    This module centralizes NoOp creation to eliminate duplication across
    CLI bootstrap modules. Runtime observability uses different bootstrap
    functions from composition/bootstrap/runtime/observability.py.
"""

from __future__ import annotations

from bioetl.domain.ports import MetricsPort, NoOpMetrics, NoOpTracing, TracingPort
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

__all__ = [
    "create_noop_logger",
    "create_noop_metrics",
    "create_noop_observability_bundle",
    "create_noop_tracing",
]


def create_noop_logger() -> NoOpLogger:
    """Create a NoOpLogger instance for CLI operations.

    Returns a logger that silently ignores all logging calls.
    Used by CLI bootstrap functions that don't require full observability.

    Returns:
        NoOpLogger instance implementing LoggerPort interface.

    Example:
        >>> logger = create_noop_logger()
        >>> logger.info("This will be silently ignored")
    """
    return NoOpLogger()


def create_noop_metrics() -> MetricsPort:
    """Create a NoOpMetrics instance for CLI operations.

    Returns a metrics collector that silently ignores all metrics.
    Uses warn_on_use=False since CLI intentionally opts out of metrics.

    Returns:
        NoOpMetrics instance implementing MetricsPort interface.

    Example:
        >>> metrics = create_noop_metrics()
        >>> metrics.increment_counter("test", 1, {"label": "value"})
    """
    return NoOpMetrics(warn_on_use=False)


def create_noop_tracing() -> TracingPort:
    """Create a NoOpTracing instance for CLI operations.

    Returns a tracer that does nothing when spans are created.
    Used when distributed tracing is not needed for CLI commands.

    Returns:
        NoOpTracing instance implementing TracingPort interface.

    Example:
        >>> tracing = create_noop_tracing()
        >>> tracer = tracing.get_tracer("cli")
        >>> with tracer.start_as_current_span("operation"):
        ...     pass  # Span is silently ignored
    """
    return NoOpTracing()


def create_noop_observability_bundle() -> tuple[NoOpLogger, MetricsPort, TracingPort]:
    """Create a complete NoOp observability bundle for CLI operations.

    Convenience function that creates all three NoOp implementations
    in a single call. Useful when a CLI bootstrap function needs
    multiple observability dependencies.

    Returns:
        Tuple of (NoOpLogger, NoOpMetrics, NoOpTracing) instances.

    Example:
        >>> logger, metrics, tracing = create_noop_observability_bundle()
        >>> # Use in service construction
        >>> service = SomeService(logger=logger, metrics=metrics)
    """
    return (
        create_noop_logger(),
        create_noop_metrics(),
        create_noop_tracing(),
    )

================================================================================
File: storage.py
Path: bootstrap\cli\storage.py
================================================================================
"""Bootstrap functions for storage-related CLI operations.

Contains bootstrap functions for maintenance services:
- CleanupService: Preview and execute cleanup operations
- MedallionLifecycleService: Vacuum and archive Delta tables
- BronzeCleanupService: Bronze layer retention cleanup
- VacuumService: Batch vacuum operations
- ExportService: Export Delta tables to various formats

Note:
    Uses NoOp observability since these are CLI operations.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bioetl.application.core.cleanup_service import CleanupService
from bioetl.application.services import (
    BronzeCleanupService,
    ExportService,
    VacuumService,
)
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.registry import get_default_registry
from bioetl.infrastructure.config import get_settings, load_pipeline_config
from bioetl.infrastructure.storage.delta_reader import DeltaReader

__all__ = [
    "bootstrap_bronze_cleanup_service",
    # Deprecated alias (backward compatibility)
    "bootstrap_cleanup",
    # Canonical name (use this)
    "bootstrap_cleanup_service",
    "bootstrap_export_service",
    "bootstrap_lifecycle_service",
    "bootstrap_vacuum_service",
]


def bootstrap_cleanup_service() -> CleanupService:
    """Create a cleanup service for CLI operations.

    Creates a CleanupService with storage and logger for cleanup operations.
    Used by CLI for --dry-run preview and actual cleanup.

    Layer: Returns application service (CleanupService).

    Returns:
        CleanupService configured for the current environment.
    """
    storage = bootstrap_storage_adapter()
    noop_logger = create_noop_logger()

    return CleanupService(storage=storage, logger=noop_logger)


def bootstrap_cleanup() -> CleanupService:
    """Bootstrap the cleanup service for CLI operations.

    .. deprecated::
        Use :func:`bootstrap_cleanup_service` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Returns:
        CleanupService configured for the current environment.
    """
    return bootstrap_cleanup_service()


def bootstrap_lifecycle_service() -> MedallionLifecycleService:
    """Bootstrap MedallionLifecycleService for CLI maintenance commands.

    Creates a MedallionLifecycleService for vacuum and archive operations.
    Used by CLI for `maintenance vacuum` and `maintenance archive` commands.

    Returns:
        MedallionLifecycleService configured for the current environment.
    """
    storage = bootstrap_storage_adapter()
    noop_logger = create_noop_logger()

    return MedallionLifecycleService(storage=storage, logger=noop_logger)


def bootstrap_bronze_cleanup_service() -> BronzeCleanupService:
    """Bootstrap BronzeCleanupService for CLI maintenance commands.

    Creates a BronzeCleanupService for Bronze layer retention cleanup.
    Used by CLI for `maintenance bronze-cleanup` command.

    Returns:
        BronzeCleanupService configured for the current environment.
    """
    storage = bootstrap_storage_adapter()
    noop_logger = create_noop_logger()

    return BronzeCleanupService(storage=storage, logger=noop_logger)


def bootstrap_vacuum_service() -> VacuumService:
    """Bootstrap VacuumService for CLI maintenance commands.

    Creates a VacuumService for batch vacuum operations.
    Used by CLI for `maintenance vacuum-all` command.

    Returns:
        VacuumService configured for the current environment.
    """
    lifecycle = bootstrap_lifecycle_service()
    noop_logger = create_noop_logger()

    # Create table collector that queries the registry (DI pattern)
    table_collector = _create_table_collector()

    return VacuumService(
        lifecycle=lifecycle,
        logger=noop_logger,
        table_collector=table_collector,
    )


def _create_table_collector() -> Callable[[str], list[tuple[str, str]]]:
    """Create a table collector function for VacuumService.

    This function queries the pipeline registry and config loader
    to collect silver/gold tables. It lives in composition layer
    to maintain proper dependency direction (application -> domain <- composition).

    Returns:
        Callable that collects tables for a given layer.

    Raises:
        ValueError: If config file for a registered pipeline is not found.
    """

    def collect_tables(layer: str) -> list[tuple[str, str]]:
        """Collect tables from all registered pipelines.

        Args:
            layer: Which layer to collect - "all", "silver", or "gold".

        Returns:
            List of (table_name, layer) tuples sorted alphabetically.

        Raises:
            ValueError: If config file for a registered pipeline is not found.
        """
        registry = get_default_registry()
        pipelines = registry.list_pipelines()

        silver_tables: set[str] = set()
        gold_tables: set[str] = set()

        for pipeline_name in pipelines:
            config = load_pipeline_config(pipeline_name)
            if config.silver_table:
                silver_tables.add(config.silver_table)
            if config.gold_table:
                gold_tables.add(config.gold_table)

        tables: list[tuple[str, str]] = []
        if layer in ("all", "silver"):
            tables.extend((t, "silver") for t in sorted(silver_tables))
        if layer in ("all", "gold"):
            tables.extend((t, "gold") for t in sorted(gold_tables))

        return tables

    return collect_tables


def bootstrap_export_service() -> ExportService:
    """Bootstrap ExportService for CLI export commands.

    Creates an ExportService for exporting Delta Lake tables to
    CSV, XLSX, and TSV formats.

    Returns:
        ExportService configured for the current environment.
    """
    settings = get_settings()
    noop_logger = create_noop_logger()

    # Use data/output/ subdirectory for actual data paths (matches pipeline configs)
    # The pipeline configs use data/output/silver, data/output/gold
    output_dir = Path(settings.data_dir) / "output"
    silver_path = output_dir / "silver"
    gold_path = output_dir / "gold"

    # Create Delta reader for Silver and Gold paths
    reader = DeltaReader(
        base_path=silver_path,  # Base path for relative paths
        logger=noop_logger,
    )

    return ExportService(
        reader=reader,
        logger=noop_logger,
        silver_path=silver_path,
        gold_path=gold_path,
        export_path=output_dir / "exports",
    )

================================================================================
File: __init__.py
Path: bootstrap\runtime\__init__.py
================================================================================
"""Runtime bootstrap module for pipeline execution.

Contains bootstrap functions for actual pipeline execution scenarios:
- Single pipeline runs (incremental, backfill, rebuild)
- Composite pipeline runs with enrichment coordination
- Full observability stack (logging, tracing, metrics, DQ monitoring)

IMPORTANT: This module MUST NOT import from bootstrap/cli/.
CLI modules may import from runtime for runner access, but not vice versa.

Components:
- assembly: Pure configuration assembly functions (no I/O)
- observability: Full observability stack bootstrap
- pipeline: Main pipeline bootstrap entry point
- composite: Composite pipeline bootstrap
- runner: PipelineRunnerService bootstrap
"""

from __future__ import annotations

from bioetl.composition.bootstrap.runtime.assembly import (
    VacuumSettings,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
)
from bioetl.composition.bootstrap.runtime.composite import (
    # Deprecated alias
    bootstrap_composite_pipeline,
    # Canonical name
    bootstrap_composite_runner,
    load_composite_config,
)
from bioetl.composition.bootstrap.runtime.observability import (
    MetricsServerError,
    # Deprecated aliases
    bootstrap_dq_monitor,
    # Canonical names
    bootstrap_dq_monitor_port,
    bootstrap_logger,
    bootstrap_logger_port,
    bootstrap_metrics,
    bootstrap_metrics_port,
    bootstrap_observability,
    bootstrap_observability_bundle,
    bootstrap_tracer,
    bootstrap_tracer_port,
    maybe_start_metrics_server,
    start_metrics_server,
    validate_observability_preflight,
)
from bioetl.composition.bootstrap.runtime.pipeline import (
    # Deprecated alias
    bootstrap_pipeline,
    # Canonical name
    bootstrap_pipeline_runner,
)
from bioetl.composition.bootstrap.runtime.runner import (
    bootstrap_pipeline_runner_service,
)

__all__ = [
    # Observability (canonical)
    "MetricsServerError",
    # Assembly (pure functions)
    "VacuumSettings",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
    # Composite (deprecated alias)
    "bootstrap_composite_pipeline",
    # Composite (canonical)
    "bootstrap_composite_runner",
    # Observability (deprecated aliases)
    "bootstrap_dq_monitor",
    "bootstrap_dq_monitor_port",
    "bootstrap_logger",
    "bootstrap_logger_port",
    "bootstrap_metrics",
    "bootstrap_metrics_port",
    "bootstrap_observability",
    "bootstrap_observability_bundle",
    # Pipeline (deprecated alias)
    "bootstrap_pipeline",
    # Pipeline (canonical)
    "bootstrap_pipeline_runner",
    # Runner service
    "bootstrap_pipeline_runner_service",
    "bootstrap_tracer",
    "bootstrap_tracer_port",
    # Utilities
    "load_composite_config",
    "maybe_start_metrics_server",
    "start_metrics_server",
    "validate_observability_preflight",
]

================================================================================
File: assembly.py
Path: bootstrap\runtime\assembly.py
================================================================================
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

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext, VacuumConfig
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterConfig as YamlInputFilter,
    )
    from bioetl.infrastructure.schemas.pipeline_config import (
        MaintenanceConfig,
    )

__all__ = [
    "VacuumSettings",
    "assemble_cached_bronze_context",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
]


@dataclass(frozen=True, slots=True)
class VacuumSettings:
    """Resolved vacuum settings after merging CLI and YAML config.

    This is a pure data object representing the effective vacuum configuration
    after applying CLI overrides to YAML defaults.

    Attributes:
        enabled: Whether vacuum should run after pipeline execution.
        retention_days: Number of days to retain data during vacuum.
    """

    enabled: bool
    retention_days: int


def assemble_vacuum_settings(
    *,
    cli_vacuum: VacuumConfig,
    yaml_maintenance: MaintenanceConfig,
) -> VacuumSettings:
    """Assemble effective vacuum settings from CLI overrides and YAML config.

    Implements tri-state merge logic:
    - CLI `enabled=None` → use YAML `auto_vacuum`
    - CLI `enabled=True/False` → explicit CLI override takes precedence

    Retention days follow same pattern: CLI override if vacuum explicitly enabled,
    otherwise YAML default.

    Args:
        cli_vacuum: Vacuum configuration from CLI (VacuumConfig with tri-state enabled).
        yaml_maintenance: Maintenance configuration from pipeline YAML.

    Returns:
        VacuumSettings with resolved enabled flag and retention days.

    Example:
        >>> from bioetl.domain.context import VacuumConfig
        >>> # CLI doesn't override -> use YAML
        >>> cli = VacuumConfig(enabled=None, retention_days=7)
        >>> yaml = MaintenanceConfig(auto_vacuum=True, vacuum_retention_days=14)
        >>> result = assemble_vacuum_settings(cli_vacuum=cli, yaml_maintenance=yaml)
        >>> result.enabled
        True
        >>> result.retention_days
        14

        >>> # CLI explicitly overrides -> use CLI values
        >>> cli = VacuumConfig(enabled=False, retention_days=3)
        >>> result = assemble_vacuum_settings(cli_vacuum=cli, yaml_maintenance=yaml)
        >>> result.enabled
        False
        >>> result.retention_days
        3
    """
    # CLI explicit override takes precedence
    if cli_vacuum.enabled is not None:
        return VacuumSettings(
            enabled=cli_vacuum.enabled,
            retention_days=cli_vacuum.retention_days,
        )

    # No CLI override -> use YAML defaults
    return VacuumSettings(
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
    vacuum: VacuumSettings,
    skip_gold: bool = False,
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
        cli_fallback_column=ctx.input_filter.fallback_column
        if ctx.input_filter.enabled
        else None,
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

================================================================================
File: composite.py
Path: bootstrap\runtime\composite.py
================================================================================
"""Bootstrap functions for Composite Pipeline execution.

Handles initialization and wiring for CompositePipelineRunner.
See ADR-026 for architectural decisions.

Composite pipelines execute multiple related pipelines in sequence:
1. Seed phase: Fetch primary entities (e.g., publications)
2. Enrichment phase: Fetch supplementary data using seed keys
3. Merge phase: Combine results into unified datasets
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import yaml
from pydantic import ValidationError

from bioetl.application.composite.checkpoint import CompositeCheckpointManager
from bioetl.application.composite.coordinator import EnrichmentCoordinator
from bioetl.application.composite.dependency_coordinator import DependencyCoordinator
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.application.composite.merger import MergeService
from bioetl.application.composite.runner import (
    CompositePipelineRunner,
    CompositeRuntimeConfig,
)
from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger_port
from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
from bioetl.domain.composite.config import (
    CompositeConfig,
    DependencyConfig,
    EnricherConfig,
)
from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.config.field_group_loader import (
    FieldGroupLoadError,
    load_field_groups,
)
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.schemas.composite_config import CompositeConfigFileSchema
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.infrastructure.config import Settings

__all__ = [
    "CompositeRuntimeConfig",
    # Deprecated alias (backward compatibility)
    "bootstrap_composite_pipeline",
    # Canonical name (use this)
    "bootstrap_composite_runner",
    "load_composite_config",
]

# Default composite config path
COMPOSITE_CONFIG_DIR = Path("configs/pipelines/composite")
FIELD_GROUP_CONFIG_DIR = Path("configs/composite/field_groups")


def load_composite_config(name: str) -> CompositeConfig:
    """Load and parse composite pipeline configuration from YAML.

    Uses Pydantic schema validation (CompositeConfigFileSchema) to ensure
    configuration is valid before converting to domain objects.

    Args:
        name: Composite pipeline name (e.g., 'publication').

    Returns:
        CompositeConfig instance.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config is invalid (wraps Pydantic ValidationError).
    """
    config_path = COMPOSITE_CONFIG_DIR / f"{name}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Composite config not found: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    merge = (raw or {}).get("composite", {}).get("merge", {})
    column_groups_file = merge.get("column_groups_file")
    if column_groups_file and "column_groups" not in merge:
        groups_path = config_path.parent / column_groups_file
        if groups_path.exists():
            with groups_path.open(encoding="utf-8") as f:
                groups_raw = yaml.safe_load(f) or {}
            if isinstance(groups_raw, list):
                merge["column_groups"] = groups_raw
            elif isinstance(groups_raw, dict):
                merge["column_groups"] = groups_raw.get("column_groups", [])

    try:
        # Validate using Pydantic schema
        schema = CompositeConfigFileSchema.model_validate(raw)
        # Convert to immutable domain objects
        config: CompositeConfig = schema.to_domain()
        return config
    except ValidationError as e:
        # Convert Pydantic errors to ValueError for consistent API
        raise ValueError(f"Invalid composite config '{name}': {e}") from e


def _build_fallback_mapping(
    keys: pl.DataFrame,
    filter_key: str,
    join_keys: tuple[str, ...],
) -> dict[str, str] | None:
    """Build ID -> Title fallback mapping if title is in join keys."""
    if "title" not in join_keys or "title" not in keys.columns:
        return None
    pairs = (
        keys.select([filter_key, "title"])
        .drop_nulls()
        .unique(subset=[filter_key])
        .iter_rows()
    )
    return {str(k): str(t) for k, t in pairs}


def _find_filter_key(
    join_keys: tuple[str, ...],
    columns: list[str],
) -> str | None:
    """Find the first usable join key (skip title if alternatives exist)."""
    for key in join_keys:
        if key == "title" and len(join_keys) > 1:
            continue
        if key in columns:
            return key
    return None


def _extract_filter_ids_from_keys(
    enricher_cfg: EnricherConfig,
    keys: pl.DataFrame,
    logger: LoggerPort | None = None,
) -> tuple[tuple[str, ...] | None, str | None, dict[str, str] | None]:
    """Extract filter IDs from seed keys for an enricher."""
    if keys is None or len(keys) == 0:
        if logger:
            logger.debug(
                "No keys available for enricher",
                pipeline=enricher_cfg.pipeline,
            )
        return None, None, None
    filter_key = _find_filter_key(enricher_cfg.join_keys, keys.columns)
    if filter_key is None:
        if logger:
            logger.warning(
                "Join key not found in keys columns",
                pipeline=enricher_cfg.pipeline,
                join_keys=list(enricher_cfg.join_keys),
                available_columns=list(keys.columns),
            )
        return None, None, None
    key_values = keys.select(filter_key).drop_nulls().unique().to_series().to_list()
    if not key_values:
        return None, None, None
    filter_ids = tuple(str(v) for v in key_values)
    fallback = _build_fallback_mapping(keys, filter_key, enricher_cfg.join_keys)
    return filter_ids, filter_key, fallback


def _extract_field_values(
    keys: pl.DataFrame,
    field: str,
) -> tuple[str, ...] | None:
    """Extract unique non-null values for a single field from keys DataFrame.

    Returns:
        Tuple of string values, or None if field missing or empty.
    """
    if field not in keys.columns:
        return None
    values = keys.select(field).drop_nulls().unique().to_series().to_list()
    if not values:
        return None
    return tuple(str(v) for v in values)


def _extract_multi_filter_ids(
    dep_cfg: DependencyConfig,
    keys: pl.DataFrame,
    logger: LoggerPort | None = None,
) -> dict[str, tuple[str, ...]] | None:
    """Extract multi-field filter IDs from seed keys for a dependency.

    For dual-key filtering (e.g., molecule_chembl_id + document_chembl_id),
    extracts unique values for each filter field from the keys DataFrame.

    Args:
        dep_cfg: Dependency configuration with filter_fields.
        keys: DataFrame containing seed keys.
        logger: Optional logger.

    Returns:
        Dict mapping field name to tuple of unique IDs, or None if extraction fails.
    """
    if keys is None or len(keys) == 0:
        return None

    result: dict[str, tuple[str, ...]] = {}
    for field in dep_cfg.effective_filter_fields:
        values = _extract_field_values(keys, field)
        if values is None:
            if logger:
                logger.warning(
                    "Multi-filter field missing or empty",
                    pipeline=dep_cfg.pipeline,
                    field=field,
                    available_columns=list(keys.columns),
                )
            return None
        result[field] = values

    if logger:
        logger.info(
            "Extracted multi-field filter IDs",
            pipeline=dep_cfg.pipeline,
            fields=list(result.keys()),
            counts={f: len(ids) for f, ids in result.items()},
        )

    return result


def _resolve_bronze_opts(
    runtime: CompositeRuntimeConfig,
    phase_override: bool | None,
) -> dict[str, object]:
    """Resolve cached Bronze options for a specific pipeline phase.

    Tri-state resolution: phase_override takes precedence over master switch.
    - None: use master switch (runtime.use_cached_bronze)
    - True/False: override master switch

    Args:
        runtime: Composite runtime configuration with master switch.
        phase_override: Per-phase override (None=follow master).

    Returns:
        Dict with use_cached_bronze, cached_bronze_path, cached_bronze_date.
    """
    effective = (
        phase_override if phase_override is not None else runtime.use_cached_bronze
    )
    return {
        "use_cached_bronze": effective,
        "cached_bronze_path": runtime.cached_bronze_path if effective else None,
        "cached_bronze_date": runtime.cached_bronze_date if effective else None,
    }


def bootstrap_composite_runner(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None = None,
) -> CompositePipelineRunner:
    """Create a CompositePipelineRunner with all dependencies.

    Layer: Returns application-level runner (CompositePipelineRunner) ready
    for execution.

    Args:
        config: Composite pipeline configuration.
        runtime: Runtime options (resume, dry_run, etc.).
        run_id: Optional run ID (generated if not provided).

    Returns:
        CompositePipelineRunner ready for execution.
    """
    # CIRCULAR-DEPENDENCY: Local import required to break circular dependency.
    # Import chain: entrypoints -> _bootstrap -> bootstrap -> runtime -> composite -> entrypoints
    # Moving this import to module level would cause ImportError at startup.
    from bioetl.composition.entrypoints import RunOptions, build_pipeline_context

    effective_run_id = run_id or str(uuid4())
    settings = get_settings()

    # Bootstrap logger (without settings - uses log_level parameter)
    logger = bootstrap_logger_port(
        pipeline=config.name,
        run_id=UUID(effective_run_id),
        log_level="INFO",
    )

    # Bootstrap storage for reading Silver tables and writing merged data
    # Enable CSV export for composite pipelines (merged Silver/Gold data)
    storage = bootstrap_storage_adapter(enable_csv_export=True)

    # Bootstrap lock (using in-memory lock for local execution)
    lock = MemoryLock()

    # Per-phase cached bronze RunOptions kwargs
    _seed_bronze_opts = _resolve_bronze_opts(runtime, phase_override=None)
    _enricher_bronze_opts = _resolve_bronze_opts(
        runtime, phase_override=runtime.cached_bronze_enrichers
    )
    _dependency_bronze_opts = _resolve_bronze_opts(
        runtime, phase_override=runtime.cached_bronze_dependencies
    )

    def seed_runner_factory() -> PipelineRunner:
        """Create PipelineRunner for the seed phase."""
        options = RunOptions(
            run_type="incremental",
            limit=runtime.seed_limit,
            skip_gold=True,
            **_seed_bronze_opts,  # type: ignore[arg-type]
        )
        ctx = build_pipeline_context(config.seed.pipeline, options)
        return bootstrap_pipeline_runner(ctx)

    # Build enricher config lookup for fast access
    enricher_configs = {e.pipeline: e for e in config.enrichers}

    def enricher_runner_factory(
        pipeline_name: str, keys: pl.DataFrame
    ) -> PipelineRunner:
        """Create PipelineRunner for an enricher phase (ADR-026)."""
        enricher_cfg = enricher_configs.get(pipeline_name)
        filter_ids: tuple[str, ...] | None = None
        filter_field: str | None = None
        fallback_mapping: dict[str, str] | None = None

        if enricher_cfg:
            filter_ids, filter_field, fallback_mapping = _extract_filter_ids_from_keys(
                enricher_cfg, keys, logger
            )

        # Debug logging for enricher filter configuration
        logger.debug(
            "Creating enricher runner",
            pipeline=pipeline_name,
            keys_columns=list(keys.columns) if keys is not None else [],
            keys_count=len(keys) if keys is not None else 0,
            join_keys=list(enricher_cfg.join_keys) if enricher_cfg else [],
            filter_field=filter_field,
            filter_ids_count=len(filter_ids) if filter_ids else 0,
            filter_ids_sample=list(filter_ids)[:5] if filter_ids else [],
        )

        # many_to_one: no limit; one_to_one: limit to seed count
        limit: int | None = None
        if enricher_cfg and enricher_cfg.is_many_to_one:
            limit = None
        elif keys is not None:
            limit = len(keys)

        options = RunOptions(
            run_type="incremental",
            limit=limit,
            ignore_yaml_filter=True,
            skip_gold=True,
            filter_ids=filter_ids,
            filter_field=filter_field,
            fallback_mapping=fallback_mapping,
            **_enricher_bronze_opts,  # type: ignore[arg-type]
        )
        ctx = build_pipeline_context(pipeline_name, options)
        return bootstrap_pipeline_runner(ctx)

    # Build dependency config lookup for fast access
    dependency_configs = {d.pipeline: d for d in config.dependencies}

    # Create dependencies runner factory
    def dependencies_runner_factory(
        pipeline_name: str, keys: pl.DataFrame
    ) -> PipelineRunner:
        """Create PipelineRunner for a dependency phase.

        Dependencies run after the seed to populate Silver tables before enrichers.
        Unlike enrichers which read from Silver, dependencies call APIs to fetch data.

        Note: Chained dependencies (key_source) are handled by DependencyCoordinator
        which provides the correct keys from the source dependency's Silver table.

        Configuration:
        - Extracts join key values from provided keys DataFrame
        - Passes extracted IDs as filter_ids to limit API calls
        - Uses filter_field from config if set (for field name mapping)
        - For multi-field filtering (filter_fields), extracts all fields
          and passes as multi_filter_ids with valid combinations

        Args:
            pipeline_name: Name of the dependency pipeline to instantiate.
            keys: DataFrame containing keys for filtering (from seed or chained source).

        Returns:
            PipelineRunner configured for dependency pipeline execution.
        """
        dep_cfg = dependency_configs.get(pipeline_name)
        filter_ids: tuple[str, ...] | None = None
        filter_field: str | None = None
        multi_filter_ids: dict[str, tuple[str, ...]] | None = None

        if dep_cfg and keys is not None and len(keys) > 0:
            if dep_cfg.is_multi_field_filter:
                # Multi-field filtering: extract all filter fields
                multi_filter_ids = _extract_multi_filter_ids(dep_cfg, keys, logger)
            else:
                # Single-field filtering (existing logic)
                for key in dep_cfg.join_keys:
                    if key in keys.columns:
                        key_values = (
                            keys.select(key).drop_nulls().unique().to_series().to_list()
                        )
                        if key_values:
                            filter_ids = tuple(str(v) for v in key_values)
                            # Use filter_field from config if set, otherwise use join_key
                            filter_field = dep_cfg.filter_field or key
                            break

        # Debug logging for dependency filter configuration
        logger.debug(
            "Creating dependency runner",
            pipeline=pipeline_name,
            keys_columns=list(keys.columns) if keys is not None else [],
            keys_count=len(keys) if keys is not None else 0,
            join_keys=list(dep_cfg.join_keys) if dep_cfg else [],
            filter_field=filter_field,
            filter_ids_count=len(filter_ids) if filter_ids else 0,
            filter_ids_sample=list(filter_ids)[:5] if filter_ids else [],
            multi_filter_fields=list(multi_filter_ids.keys())
            if multi_filter_ids
            else [],
            multi_filter_counts={f: len(ids) for f, ids in multi_filter_ids.items()}
            if multi_filter_ids
            else {},
            is_chained=dep_cfg.key_source is not None if dep_cfg else False,
            key_source=dep_cfg.key_source if dep_cfg else None,
        )

        options = RunOptions(
            run_type="incremental",
            limit=len(keys)
            if (filter_ids or multi_filter_ids) and keys is not None
            else None,
            filter_ids=filter_ids,
            filter_field=filter_field,
            multi_filter_ids=multi_filter_ids,
            ignore_yaml_filter=True,
            skip_gold=True,
            **_dependency_bronze_opts,  # type: ignore[arg-type]
        )
        ctx = build_pipeline_context(pipeline_name, options)
        return bootstrap_pipeline_runner(ctx)

    # Create services
    # Base path for resolving Silver table locations
    silver_base_path = str(Path(settings.data_dir) / "output")

    # DeltaReader for reading Silver tables (implements DeltaReaderPort)
    delta_reader = DeltaReader(
        base_path=silver_base_path,
        logger=logger,
    )

    key_extractor = KeyExtractorService(
        delta_reader=delta_reader,
        logger=logger,
    )

    dependency_coordinator = DependencyCoordinator(
        logger=logger,
        delta_reader=delta_reader,
    )

    coordinator = EnrichmentCoordinator(
        logger=logger,
        dq_config=config.dq,
        max_concurrency=config.execution.max_concurrency,
    )

    # Load field group registry for semantic column grouping and Gold filtering
    field_group_registry = _load_field_group_registry(config.name, logger)

    merger = MergeService(
        merge_config=config.merge,
        storage=storage,
        logger=logger,
        delta_reader=delta_reader,
        field_group_registry=field_group_registry,
    )

    checkpoint_dir = Path(settings.data_dir) / "checkpoints" / "composite"
    checkpoint_manager = CompositeCheckpointManager(
        composite_name=config.name,
        run_id=effective_run_id,
        checkpoint_dir=checkpoint_dir,
        logger=logger,
        resume=runtime.resume,
    )

    # Create DQ report service for composite
    dq_report_service = _create_dq_report_service(logger, settings)

    return CompositePipelineRunner(
        config=config,
        runtime=runtime,
        seed_runner_factory=seed_runner_factory,
        dependencies_runner_factory=dependencies_runner_factory,
        enricher_runner_factory=enricher_runner_factory,
        key_extractor=key_extractor,
        dependency_coordinator=dependency_coordinator,
        coordinator=coordinator,
        merger=merger,
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        lock=lock,
        run_id=effective_run_id,
        dq_report_service=dq_report_service,
    )


def bootstrap_composite_pipeline(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    run_id: str | None = None,
) -> CompositePipelineRunner:
    """Bootstrap a CompositePipelineRunner with all dependencies.

    .. deprecated::
        Use :func:`bootstrap_composite_runner` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        config: Composite pipeline configuration.
        runtime: Runtime options (resume, dry_run, etc.).
        run_id: Optional run ID (generated if not provided).

    Returns:
        CompositePipelineRunner ready for execution.
    """
    return bootstrap_composite_runner(config=config, runtime=runtime, run_id=run_id)


def _load_field_group_registry(
    composite_name: str,
    logger: LoggerPort,
) -> FieldGroupRegistry | None:
    """Load field group registry for a composite pipeline.

    Attempts to load field group configuration from YAML. Returns None
    if no configuration is found (graceful degradation).

    Args:
        composite_name: Composite pipeline name (e.g., "composite_publication").
        logger: Structured logger.

    Returns:
        FieldGroupRegistry if config found, None otherwise.
    """
    # Extract entity from composite name (e.g., "composite_publication" -> "publication")
    entity = (
        composite_name.replace("composite_", "")
        if "_" in composite_name
        else composite_name
    )
    config_path = FIELD_GROUP_CONFIG_DIR / f"{entity}.yaml"

    if not config_path.exists():
        logger.debug(
            "No field group config found, skipping",
            config_path=str(config_path),
        )
        return None

    try:
        registry = load_field_groups(config_path)
        logger.info(
            "Loaded field group registry",
            config_path=str(config_path),
            groups=len(registry.groups),
            fields=registry.field_count,
            columns=registry.column_count,
        )
        return registry
    except (FieldGroupLoadError, FileNotFoundError) as e:
        logger.warning(
            "Failed to load field group config, continuing without it",
            error=str(e),
            config_path=str(config_path),
        )
        return None


def _create_dq_report_service(
    logger: LoggerPort,
    settings: Settings,
) -> DQReportService:
    """Create DQ report service for composite pipelines.

    Args:
        logger: Structured logger.
        settings: Application settings.

    Returns:
        DQReportService instance.

    Raises:
        ImportError: If required modules are not available.
    """
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.infrastructure.export.dq_report_writer import DQReportWriter

    # Create DQ report writer
    reports_base_path = Path(settings.data_dir) / "output" / "reports" / "dq"
    report_writer = DQReportWriter(
        base_path=reports_base_path,
        logger=logger,
    )

    return DQReportService(
        logger=logger,
        report_writer=report_writer,
    )

================================================================================
File: observability.py
Path: bootstrap\runtime\observability.py
================================================================================
"""Bootstrap functions for runtime observability components.

Contains bootstrap functions for logging, tracing, metrics, and data quality
monitoring. These functions configure the full observability stack for
pipeline execution.

Unified Observability Contract:
- bootstrap_observability() always returns valid implementations
- Logger: UnifiedLogger with Log Schema enforcement (run_id, pipeline, stage)
- Metrics: PrometheusMetrics or NoOpMetrics (never None)
- Tracer: OpenTelemetryTracer or NoOpTracing (never None)
- DQMonitor: DataQualityMonitor or None (optional)

Note:
    CLI uses NoOp implementations via bootstrap/cli/metrics.py.
    This module provides full observability for runtime execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import (
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    NoOpMetrics,
    NoOpTracing,
    TracingPort,
)
from bioetl.infrastructure.observability import (
    OpenTelemetryTracer,
    PrometheusMetrics,
    UnifiedLogger,
    start_metrics_server,
)
from bioetl.infrastructure.observability.anomaly import DataQualityMonitor
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings

__all__ = [
    "MetricsServerError",
    # Deprecated aliases (backward compatibility)
    "bootstrap_dq_monitor",
    # Canonical names (use these)
    "bootstrap_dq_monitor_port",
    "bootstrap_logger",
    "bootstrap_logger_port",
    "bootstrap_metrics",
    "bootstrap_metrics_port",
    "bootstrap_observability",
    "bootstrap_observability_bundle",
    "bootstrap_tracer",
    "bootstrap_tracer_port",
    "maybe_start_metrics_server",
    "start_metrics_server",
    "validate_observability_preflight",
]


def validate_observability_preflight(
    tracer: TracingPort,
    metrics: MetricsPort,
    environment: str,
    logger: LoggerPort,
) -> None:
    """Validate observability components for production readiness.

    Performs preflight validation to detect NoOp implementations in production.
    Emits warnings when observability data will be lost due to NoOp fallbacks.

    This function helps prevent silent data loss in production environments
    where NoOpTracing or NoOpMetrics would discard traces/metrics without
    any visible indication.

    Args:
        tracer: The tracing port implementation (may be NoOpTracing).
        metrics: The metrics port implementation (may be NoOpMetrics).
        environment: Environment name from settings (e.g., "dev", "staging", "prod").
        logger: Logger for emitting warnings.

    Note:
        In non-production environments, NoOp implementations are acceptable
        and no warnings are emitted.
    """
    if environment != "prod":
        return

    if isinstance(tracer, NoOpTracing):
        logger.warning(
            "noop_tracing_in_production",
            message="NoOpTracing in production - traces will be lost",
            recommendation="Set BIOETL_OBSERVABILITY__TRACING_ENABLED=true "
            "and configure OpenTelemetry endpoint",
        )

    if isinstance(metrics, NoOpMetrics):
        logger.warning(
            "noop_metrics_in_production",
            message="NoOpMetrics in production - metrics will be lost",
            recommendation="Set BIOETL_OBSERVABILITY__METRICS_ENABLED=true "
            "to enable Prometheus metrics collection",
        )


def bootstrap_logger_port(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
) -> LoggerPort:
    """Create a logger port implementation for pipeline execution.

    Uses UnifiedLogger which enforces the Log Schema from RULES.md §3.2.1:
    - Mandatory fields: run_id, pipeline (bound at initialization)
    - Stage field: defaults to "init" for LoggerPort compatibility

    Layer: Returns domain port implementation (LoggerPort).

    Args:
        pipeline: Pipeline name for logger context.
        run_id: Unique run identifier. If None, generates a new UUID.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.

    Returns:
        UnifiedLogger implementing LoggerPort with Log Schema enforcement.
    """
    effective_run_id = run_id if run_id is not None else uuid4()
    return UnifiedLogger(
        pipeline=pipeline,
        run_id=effective_run_id,
        log_level=log_level,
        json_format=True,
    )


def bootstrap_logger(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
) -> LoggerPort:
    """Create a logger for pipeline execution.

    .. deprecated::
        Use :func:`bootstrap_logger_port` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        pipeline: Pipeline name for logger context.
        run_id: Unique run identifier. If None, generates a new UUID.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.

    Returns:
        UnifiedLogger implementing LoggerPort with Log Schema enforcement.
    """
    return bootstrap_logger_port(pipeline=pipeline, run_id=run_id, log_level=log_level)


def bootstrap_tracer_port(
    settings: Settings,
    service_name: str = "bioetl",
) -> TracingPort:
    """Create a tracing port implementation for distributed tracing.

    When tracing is disabled, returns NoOpTracing.
    When tracing is enabled, returns OpenTelemetryTracer.

    Layer: Returns domain port implementation (TracingPort).

    Args:
        settings: Application settings (MUST be injected, not loaded globally).
        service_name: Name of the service for tracing context.

    Returns:
        TracingPort instance (OpenTelemetryTracer or NoOpTracing).

    Raises:
        ImportError: If tracing is enabled but OpenTelemetry is not installed.
    """
    if settings.observability.tracing_enabled:
        return OpenTelemetryTracer(service_name=service_name)
    return NoOpTracing()


def bootstrap_tracer(
    settings: Settings,
    service_name: str = "bioetl",
) -> TracingPort:
    """Bootstrap distributed tracing for runtime execution.

    .. deprecated::
        Use :func:`bootstrap_tracer_port` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        settings: Application settings (MUST be injected, not loaded globally).
        service_name: Name of the service for tracing context.

    Returns:
        TracingPort instance (OpenTelemetryTracer or NoOpTracing).
    """
    return bootstrap_tracer_port(settings=settings, service_name=service_name)


def bootstrap_metrics_port(settings: Settings) -> MetricsPort:
    """Create a metrics port implementation.

    Unified Observability Contract: Always returns a valid MetricsPort.
    When metrics are disabled, returns NoOpMetrics (silent fallback).

    Note:
        This function only creates the metrics collector.
        Server startup is handled separately by entrypoints via
        maybe_start_metrics_server() to keep bootstrap side-effect free.

    Layer: Returns domain port implementation (MetricsPort).

    Args:
        settings: Application settings.

    Returns:
        MetricsPort instance (PrometheusMetrics or NoOpMetrics).
        Never returns None - uses NoOpMetrics as fallback.
    """
    if not settings.observability.metrics_enabled:
        # Silent fallback - no warning since explicitly disabled
        return NoOpMetrics(warn_on_use=False)

    return PrometheusMetrics()


def maybe_start_metrics_server(settings: Settings) -> bool:
    """Start metrics server if enabled in settings.

    This function should be called by entrypoints (CLI, REST API) after
    bootstrap to start the Prometheus HTTP server. Separating server
    startup from bootstrap keeps the composition layer side-effect free.

    Args:
        settings: Application settings.

    Returns:
        True if server was started or already running, False if disabled
        or failed to start.

    Raises:
        MetricsServerError: If fail_fast=True and server fails to start.
    """
    if not settings.observability.metrics_enabled:
        return False

    if not settings.observability.metrics_server_enabled:
        return False

    obs = settings.observability

    # Start metrics server - let exceptions propagate to entrypoints
    return start_metrics_server(
        port=settings.metrics_port,
        fail_fast=obs.metrics_fail_fast,
        retry_count=obs.metrics_retry_count,
        retry_delay=obs.metrics_retry_delay,
    )


def bootstrap_metrics(settings: Settings) -> MetricsPort:
    """Bootstrap metrics with optional server start for runtime execution.

    .. deprecated::
        Use :func:`bootstrap_metrics_port` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        settings: Application settings.

    Returns:
        MetricsPort instance (PrometheusMetrics or NoOpMetrics).

    Raises:
        MetricsServerError: If fail_fast=True and server fails to start.
    """
    return bootstrap_metrics_port(settings=settings)


def bootstrap_dq_monitor_port(
    settings: Settings, logger: LoggerPort | None = None
) -> DQMonitorPort | None:
    """Create a data quality monitor port implementation.

    Creates a DataQualityMonitor configured with settings from ObservabilitySettings.
    Returns None if dq_monitor_enabled=False.

    Layer: Returns domain port implementation (DQMonitorPort) or None.

    Args:
        settings: Application settings.
        logger: Optional logger for DQ monitor. If None, uses NoOpLogger.

    Returns:
        Configured DQMonitorPort or None if disabled.
    """
    obs_settings = settings.observability

    if not obs_settings.dq_monitor_enabled:
        return None

    effective_logger = logger if logger is not None else NoOpLogger()

    monitor = DataQualityMonitor(
        logger=effective_logger,
        baseline_window=obs_settings.dq_baseline_window,
        z_score_threshold=obs_settings.dq_z_score_threshold,
    )

    # Configure min baseline samples
    monitor.detector.min_baseline_samples = obs_settings.dq_min_baseline_samples

    # Set absolute thresholds for critical metrics
    monitor.detector.set_threshold(
        "error_rate",
        min_value=0.0,
        max_value=obs_settings.dq_error_rate_max,
    )
    monitor.detector.set_threshold(
        "quality_score",
        min_value=obs_settings.dq_quality_score_min,
        max_value=1.0,
    )

    return monitor


def bootstrap_dq_monitor(
    settings: Settings, logger: LoggerPort | None = None
) -> DQMonitorPort | None:
    """Bootstrap data quality monitor for anomaly detection.

    .. deprecated::
        Use :func:`bootstrap_dq_monitor_port` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        settings: Application settings.
        logger: Optional logger for DQ monitor. If None, uses NoOpLogger.

    Returns:
        Configured DQMonitorPort or None if disabled.
    """
    return bootstrap_dq_monitor_port(settings=settings, logger=logger)


def bootstrap_observability_bundle(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str = "INFO",
) -> ObservabilityBundle:
    """Create a complete observability bundle for pipeline execution.

    Unified Observability Contract:
    - Always returns a valid ObservabilityBundle with non-None logger and metrics
    - Logger: UnifiedLogger with Log Schema enforcement (run_id, pipeline, stage)
    - Fallback to NoOpMetrics when Prometheus is disabled
    - Tracer and DQ monitor remain optional

    Creates a unified observability bundle containing logger, tracer, metrics,
    and data quality monitor.

    Layer: Returns application-level bundle (ObservabilityBundle) containing
    port implementations.

    Args:
        pipeline: Pipeline name for logger context.
        run_id: Unique run identifier.
        settings: Application settings.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.

    Returns:
        Configured ObservabilityBundle instance with valid implementations.
        Logger and metrics are guaranteed to be non-None.

    Raises:
        ObservabilityContractError: If bundle creation fails validation.
    """
    logger = bootstrap_logger_port(
        pipeline=pipeline, run_id=run_id, log_level=log_level
    )
    tracer = bootstrap_tracer_port(settings)
    metrics = bootstrap_metrics_port(settings)
    dq_monitor = bootstrap_dq_monitor_port(settings, logger)

    bundle = ObservabilityBundle(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )

    # Log observability initialization status
    logger.info(
        "observability_initialized",
        extra={
            "stage": "bootstrap",
            "metrics_type": type(metrics).__name__,
            "tracer_type": type(tracer).__name__,
            "dq_monitor_enabled": dq_monitor is not None,
        },
    )

    # Preflight validation: warn if NoOp implementations in production
    validate_observability_preflight(
        tracer=tracer,
        metrics=metrics,
        environment=settings.env,
        logger=logger,
    )

    return bundle


def bootstrap_observability(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str = "INFO",
) -> ObservabilityBundle:
    """Bootstrap all observability components for pipeline execution.

    .. deprecated::
        Use :func:`bootstrap_observability_bundle` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        pipeline: Pipeline name for logger context.
        run_id: Unique run identifier.
        settings: Application settings.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.

    Returns:
        Configured ObservabilityBundle instance with valid implementations.

    Raises:
        ObservabilityContractError: If bundle creation fails validation.
    """
    return bootstrap_observability_bundle(
        pipeline=pipeline, run_id=run_id, settings=settings, log_level=log_level
    )

================================================================================
File: pipeline.py
Path: bootstrap\runtime\pipeline.py
================================================================================
"""Bootstrap function for main pipeline execution.

Contains the primary Composition Root entry point for creating
a fully configured PipelineRunner ready for execution.

This is the main entry point for runtime pipeline execution.
CLI commands should use this via composition/entrypoints.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime.assembly import (
    assemble_cached_bronze_context,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
)
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_observability_bundle,
)
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.providers.registration import register_all_providers
from bioetl.composition.registry import PipelineRegistry, get_default_registry
from bioetl.infrastructure.config import get_settings, load_pipeline_config

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import PipelineRunContext

__all__ = [
    # Deprecated alias (backward compatibility)
    "bootstrap_pipeline",
    # Canonical name (use this)
    "bootstrap_pipeline_runner",
]


def bootstrap_pipeline_runner(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
) -> PipelineRunner:
    """Composition Root: Assembles and returns a fully configured PipelineRunner.

    This is the main entry point for creating a pipeline runner. It:
    1. Registers all providers and pipelines (idempotent)
    2. Loads settings and YAML configuration
    3. Bootstraps observability (logging, tracing, metrics)
    4. Builds filter configuration from CLI/YAML
    5. Delegates to the appropriate factory to create the runner

    Layer: Returns application-level runner (PipelineRunner) ready for execution.

    Args:
        ctx: Pipeline run context containing launch parameters including
            pipeline_name, run_id, run_type, resume flag, limit, filters, etc.
        registry: Optional PipelineRegistry instance. If None, uses the
            default global registry. Pass a custom registry for test isolation.

    Returns:
        PipelineRunner: Fully configured runner ready for execution.

    Example:
        >>> from bioetl.domain.context import PipelineRunContext
        >>> from bioetl.domain.types import RunType
        >>> from uuid import uuid4
        >>>
        >>> ctx = PipelineRunContext(
        ...     pipeline_name="chembl_activity",
        ...     run_id=uuid4(),
        ...     run_type=RunType.INCREMENTAL,
        ... )
        >>> runner = bootstrap_pipeline_runner(ctx)
        >>> await runner.run()

        # For test isolation:
        >>> from bioetl.composition.registry import create_registry
        >>> registry = create_registry()
        >>> register_all_pipelines(registry=registry)
        >>> runner = bootstrap_pipeline_runner(ctx, registry=registry)
    """
    # Use provided registry or default
    effective_registry = registry if registry is not None else get_default_registry()

    # Explicit registration (idempotent for default registry)
    register_all_providers()
    register_all_pipelines(registry=registry)

    settings = get_settings()

    # Load validated YAML config first to check for existence
    yaml_config = load_pipeline_config(ctx.pipeline_name)

    # Bootstrap unified observability (includes metrics server start if enabled)
    observability = bootstrap_observability_bundle(
        pipeline=ctx.pipeline_name,
        run_id=ctx.run_id,
        settings=settings,
        log_level=ctx.log_level,
    )

    # Assemble vacuum settings (CLI overrides YAML)
    vacuum = assemble_vacuum_settings(
        cli_vacuum=ctx.vacuum,
        yaml_maintenance=yaml_config.maintenance,
    )

    # Assemble runtime config from resolved parameters
    runtime_config = assemble_runtime_config(
        run_type=ctx.run_type,
        resume=ctx.resume,
        limit=ctx.limit,
        query=ctx.query,
        dry_run=ctx.dry_run,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
        vacuum=vacuum,
        skip_gold=ctx.skip_gold,
    )

    # Assemble filter config (CLI/direct IDs override YAML)
    filter_config = assemble_filter_config(
        yaml_filter=yaml_config.input_filter,
        ctx=ctx,
        test_mode=settings.test_mode,
    )

    if filter_config:
        observability.logger.info(
            "input_filter_enabled",
            csv_path=filter_config.source_path,
            column=filter_config.column_name,
            filter_field=filter_config.filter_field,
            source="cli" if ctx.input_filter.enabled else "config",
        )

    # Assemble cached bronze context
    cached_bronze = assemble_cached_bronze_context(ctx)

    if cached_bronze.enabled:
        observability.logger.info(
            "cached_bronze_mode_enabled",
            bronze_path=cached_bronze.bronze_path,
            bronze_date=cached_bronze.bronze_date,
        )

    # Resolve pipeline factory and delegate runner creation
    pipeline_def = effective_registry.get(ctx.pipeline_name)
    factory = pipeline_def.factory

    return factory.create_runner(
        run_id=ctx.run_id,
        runtime=runtime_config,
        settings=settings,
        observability=observability,
        filter_config=filter_config,
        config=yaml_config,
        cached_bronze=cached_bronze,
    )


def bootstrap_pipeline(
    ctx: PipelineRunContext,
    registry: PipelineRegistry | None = None,
) -> PipelineRunner:
    """Composition Root: Assembles and returns a fully configured PipelineRunner.

    .. deprecated::
        Use :func:`bootstrap_pipeline_runner` instead. This alias is kept for
        backward compatibility and will be removed in a future version.

    Args:
        ctx: Pipeline run context containing launch parameters.
        registry: Optional PipelineRegistry instance.

    Returns:
        PipelineRunner: Fully configured runner ready for execution.
    """
    return bootstrap_pipeline_runner(ctx=ctx, registry=registry)

================================================================================
File: runner.py
Path: bootstrap\runtime\runner.py
================================================================================
"""Bootstrap functions for pipeline runner service.

Provides bootstrap functions for PipelineRunnerService assembly.
This service provides a unified interface for running pipelines
from any orchestration layer (CLI, REST API, etc.).
"""

from __future__ import annotations

from uuid import uuid4

from bioetl.application.services import PipelineRunnerService
from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger_port
from bioetl.composition.factories.runner_factory import (
    create_metrics_extractor,
    create_runner_factory,
)
from bioetl.composition.registry import PipelineRegistry

__all__ = ["bootstrap_pipeline_runner_service"]


def bootstrap_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Bootstrap the PipelineRunnerService with all dependencies.

    Creates a fully configured PipelineRunnerService that can be used
    to run pipelines from any interface (CLI, REST API, etc.).

    Args:
        registry: Optional custom registry for test isolation.
            If None, uses the default global registry.

    Returns:
        PipelineRunnerService ready for use.

    Example:
        >>> service = bootstrap_pipeline_runner_service()
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> result = await service.run("chembl_activity", options=options)
    """
    # Bootstrap logger for the service (using a unique ID for service-level logging)
    logger = bootstrap_logger_port(
        pipeline="pipeline_runner_service",
        run_id=uuid4(),
        log_level="INFO",
    )

    # Create factory and extractor
    runner_factory = create_runner_factory(registry=registry)
    metrics_extractor = create_metrics_extractor()

    return PipelineRunnerService(
        runner_factory=runner_factory,
        metrics_extractor=metrics_extractor,
        logger=logger,
    )

================================================================================
File: bootstrap_contexts.py
Path: bootstrap_contexts.py
================================================================================
"""Typed contexts for bootstrap functions returning multiple dependencies.

This module provides frozen dataclasses that replace untyped tuples
in bootstrap and factory functions, enabling IDE autocomplete and
type-safe access to returned dependencies.

All contexts are immutable (frozen=True) and contain only data, no logic.

Usage:
    >>> context = PipelineCallbacksContext(
    ...     transform=transform_fn,
    ...     gold_filter=filter_fn,
    ...     gold_transform=gold_transform_fn,
    ... )
    >>> context.transform  # IDE autocomplete works
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.domain.resilience import CircuitBreakerConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        SilverDQConfigPort,
    )


__all__ = [
    "CircuitBreakerConfig",
    "DQConfigsContext",
    "DQOutputPathsContext",
    "PipelineCallbacksContext",
    "RateLimitConfig",
]


@dataclass(frozen=True)
class PipelineCallbacksContext:
    """Typed context for pipeline transformation callbacks.

    Replaces untyped tuple[Any, Any, Any] from extract_pipeline_callbacks().

    The callback types use Any for compatibility with various transformer
    implementations (TypedDict-based BronzeRecord/SilverRecord vs dict[str, Any]).

    Attributes:
        transform: Bronze to Silver transformation callback.
            Expected signature: (context, record, index) -> Awaitable[dict | None]
            Implements TransformCallback protocol.
        gold_filter: Callback to determine if record should be written to Gold.
            Expected signature: (context, record) -> bool
            Implements GoldFilterCallback protocol.
        gold_transform: Silver to Gold transformation callback.
            Expected signature: (context, silver_record) -> dict
            Implements GoldTransformCallback protocol.
    """

    transform: Any  # TransformCallback protocol
    gold_filter: Any  # GoldFilterCallback protocol
    gold_transform: Any  # GoldTransformCallback protocol


@dataclass(frozen=True)
class DQConfigsContext:
    """Typed context for Data Quality report configurations.

    Replaces untyped tuple[BronzeDQConfigPort | None, SilverDQConfigPort | None,
    GoldDQConfigPort | None] from _extract_dq_configs().

    Attributes:
        bronze: DQ report configuration for Bronze layer (None if disabled).
        silver: DQ report configuration for Silver layer (None if disabled).
        gold: DQ report configuration for Gold layer (None if disabled).
    """

    bronze: BronzeDQConfigPort | None
    silver: SilverDQConfigPort | None
    gold: GoldDQConfigPort | None


@dataclass(frozen=True)
class DQOutputPathsContext:
    """Typed context for DQ report output paths.

    Replaces untyped tuple[str | None, str | None, str | None, bool]
    from _extract_dq_output_paths().

    Attributes:
        bronze_path: Output path for Bronze DQ reports (None if not configured).
        silver_path: Output path for Silver DQ reports (None if not configured).
        gold_path: Output path for Gold DQ reports (None if not configured).
        flat_structure: Whether to use flat directory structure for DQ reports.
    """

    bronze_path: str | None
    silver_path: str | None
    gold_path: str | None
    flat_structure: bool = False


@dataclass(frozen=True)
class RateLimitConfig:
    """Typed context for rate limiting configuration.

    Replaces untyped tuple[float, int] from _get_rate_limit_from_config().

    Attributes:
        rate: Requests per second.
        capacity: Token bucket capacity (burst limit).
    """

    rate: float
    capacity: int


# CircuitBreakerConfig is imported from bioetl.domain.resilience (canonical definition)
# and re-exported via __all__ for backward compatibility.

================================================================================
File: bootstrap_logger.py
Path: bootstrap_logger.py
================================================================================
"""Bootstrap-phase structured logging for composition layer.

Provides structured logging for the composition layer during bootstrap,
before run_id is available. Uses structlog for consistent output format
with pipeline execution logs.

Key differences from pipeline LoggerPort:
- No run_id binding (uses "bootstrap" sentinel)
- stage is always "bootstrap"
- Intended for configuration/registration logging only

Usage:
    from bioetl.composition.bootstrap_logger import get_bootstrap_logger

    logger = get_bootstrap_logger()
    logger.debug("config_loaded", provider="chembl", source="yaml")

Requirements:
- SHOULD: Structured logging in composition layer (audit-2026-01-06)
- REQ-OBS-004: Structured JSON format
"""

from __future__ import annotations

from typing import Any

import structlog

from bioetl.infrastructure.observability.logging_config import (
    configure_logging,
    is_logging_configured,
)

# Module-level cached logger instance
_bootstrap_logger: structlog.stdlib.BoundLogger | None = None


def get_bootstrap_logger() -> structlog.stdlib.BoundLogger:
    """Get a structured logger for bootstrap-phase logging.

    Returns a structlog logger pre-bound with bootstrap context:
    - run_id: "bootstrap" (sentinel value, no actual run_id yet)
    - stage: "bootstrap"

    The logger is cached at module level for efficiency.
    Ensures structlog is configured before use.

    Returns:
        Bound structlog logger with bootstrap context.

    Example:
        >>> logger = get_bootstrap_logger()
        >>> logger.debug("source_config_loaded", provider="chembl")
        >>> logger.warning("config_fallback", provider="pubchem", reason="yaml_not_found")
    """
    global _bootstrap_logger

    if _bootstrap_logger is not None:
        return _bootstrap_logger

    # Ensure structlog is configured (idempotent)
    if not is_logging_configured():
        configure_logging(json_format=True, log_level="INFO")

    # Create logger with bootstrap context
    base_logger = structlog.get_logger("bioetl.composition.bootstrap")
    _bootstrap_logger = base_logger.bind(
        run_id="bootstrap",
        stage="bootstrap",
    )

    return _bootstrap_logger


def reset_bootstrap_logger() -> None:
    """Reset the cached bootstrap logger (for testing only).

    Warning:
        This is intended for test fixtures only. Do not use in production code.
    """
    global _bootstrap_logger
    _bootstrap_logger = None


class BootstrapLogger:
    """Wrapper class providing LoggerPort-like interface for bootstrap phase.

    Provides familiar info/debug/warning/error methods while using
    structlog under the hood with bootstrap context pre-bound.

    Example:
        >>> logger = BootstrapLogger()
        >>> logger.debug("loading_config", provider="chembl")
        >>> logger.warning("fallback_defaults", provider="pubchem")
    """

    __slots__ = ("_logger",)

    def __init__(self) -> None:
        """Initialize with the bootstrap logger."""
        self._logger = get_bootstrap_logger()

    def debug(self, event: str, **kwargs: Any) -> None:
        """Log a debug message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.debug(event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        """Log an informational message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.info(event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        """Log a warning message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.warning(event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        """Log an error message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.error(event, **kwargs)


BOOTSTRAP_LOGGER_EXPORTS = (BootstrapLogger, reset_bootstrap_logger)

__all__ = [
    "BootstrapLogger",
    "get_bootstrap_logger",
    "reset_bootstrap_logger",
]

================================================================================
File: builders.py
Path: builders.py
================================================================================
"""Configuration builders for composition.

Encapsulates logic for constructing configuration objects from multiple sources
(e.g., merging YAML config with CLI arguments).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.filtering import FilterColumn, InputFilterConfig

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterConfig as YamlInputFilter,
    )


class FilterConfigBuilder:
    """Builder for InputFilterConfig."""

    @staticmethod
    def _is_filter_enabled(
        yaml_filter: YamlInputFilter, cli_csv: str | None, test_mode: bool
    ) -> bool:
        """Determine if filtering should be enabled."""
        if test_mode:
            return bool(cli_csv)
        return bool(cli_csv) or yaml_filter.enabled

    @staticmethod
    def _build_multi_column_config(
        yaml_filter: YamlInputFilter, effective_csv: str
    ) -> InputFilterConfig:
        """Build config for multi-column filtering mode.

        Caller must ensure yaml_filter.columns is not None.
        """
        assert yaml_filter.columns is not None  # Guaranteed by caller check
        domain_columns = tuple(
            FilterColumn(
                column_name=col.column_name,
                filter_field=col.filter_field,
            )
            for col in yaml_filter.columns
        )
        return InputFilterConfig(
            enabled=True,
            source_path=effective_csv,
            columns=domain_columns,
            batch_size=yaml_filter.batch_size,
        )

    @staticmethod
    def _build_single_column_config(
        yaml_filter: YamlInputFilter,
        effective_csv: str,
        cli_column: str | None,
        cli_field: str | None,
        cli_fallback_column: str | None,
    ) -> InputFilterConfig:
        """Build config for single-column filtering mode."""
        effective_column = cli_column or yaml_filter.column_name
        effective_field = cli_field or yaml_filter.filter_field
        effective_fallback = cli_fallback_column or yaml_filter.fallback_column
        return InputFilterConfig(
            enabled=True,
            source_path=effective_csv,
            column_name=effective_column,
            filter_field=effective_field,
            batch_size=yaml_filter.batch_size,
            fallback_column=effective_fallback,
        )

    @staticmethod
    def from_direct_ids(
        filter_ids: tuple[str, ...],
        filter_field: str,
        batch_size: int = 100,
        fallback_mapping: dict[str, str] | None = None,
    ) -> InputFilterConfig:
        """Build config for direct filter IDs mode (no CSV file).

        Used for composite pipelines where IDs are passed programmatically.
        """
        return InputFilterConfig(
            enabled=True,
            filter_field=filter_field,
            direct_filter_ids=filter_ids,
            direct_fallback_mapping=fallback_mapping,
            batch_size=batch_size,
        )

    @staticmethod
    def from_direct_multi_ids(
        multi_filter_ids: dict[str, tuple[str, ...]],
        valid_combinations: frozenset[tuple[str, ...]] | None = None,
        batch_size: int = 100,
    ) -> InputFilterConfig:
        """Build config for direct multi-field filter IDs mode.

        Used for composite dependencies that filter by multiple fields
        simultaneously (AND logic). E.g., compound_record filtered by both
        molecule_chembl_id and document_chembl_id.

        Args:
            multi_filter_ids: Mapping of field name to tuple of IDs.
            valid_combinations: Valid (field1, field2, ...) tuples for
                client-side combination filtering.
            batch_size: Number of IDs per API request.
        """
        return InputFilterConfig(
            enabled=True,
            direct_multi_filter_ids=multi_filter_ids,
            direct_valid_combinations=valid_combinations,
            batch_size=batch_size,
        )

    @staticmethod
    def build(
        yaml_filter: YamlInputFilter,
        cli_csv: str | None = None,
        cli_column: str | None = None,
        cli_field: str | None = None,
        cli_fallback_column: str | None = None,
        *,
        test_mode: bool = False,
        direct_filter_ids: tuple[str, ...] | None = None,
        direct_fallback_mapping: dict[str, str] | None = None,
        direct_multi_filter_ids: dict[str, tuple[str, ...]] | None = None,
        direct_valid_combinations: frozenset[tuple[str, ...]] | None = None,
    ) -> InputFilterConfig | None:
        """Build InputFilterConfig by merging YAML config and CLI overrides.

        Priority:
        1. direct_multi_filter_ids: Multi-field AND filtering (highest, composite)
        2. direct_filter_ids: Direct IDs (composite mode)
        3. cli_csv: CSV path from CLI
        4. yaml_filter: YAML config (disabled in test_mode)

        Multi-column mode (columns list in YAML) is used as-is, CLI overrides ignored.

        Note:
            In test mode, YAML-based filters are disabled to allow E2E tests
            to run without requiring actual filter CSV files.

        Args:
            yaml_filter: Filter configuration from pipeline YAML
            cli_csv: Optional CSV path from CLI (single-column mode only)
            cli_column: Optional column name from CLI (single-column mode only)
            cli_field: Optional filter field from CLI (single-column mode only)
            cli_fallback_column: Optional fallback column from CLI
            test_mode: If True, YAML-based filters are disabled
            direct_filter_ids: Direct filter IDs (no CSV file, for composite mode)
            direct_fallback_mapping: Direct fallback mapping (DOI->Title)
            direct_multi_filter_ids: Multi-field filter IDs (AND logic, composite)
            direct_valid_combinations: Valid (field1, field2) tuples for
                client-side combination filtering

        Returns:
            Configured InputFilterConfig or None if filtering is disabled
        """
        # Direct multi-field filter IDs take highest priority
        if direct_multi_filter_ids is not None:
            return FilterConfigBuilder.from_direct_multi_ids(
                multi_filter_ids=direct_multi_filter_ids,
                valid_combinations=direct_valid_combinations,
                batch_size=yaml_filter.batch_size,
            )

        # Direct filter IDs take highest priority (composite mode)
        if direct_filter_ids is not None:
            return FilterConfigBuilder.from_direct_ids(
                filter_ids=direct_filter_ids,
                filter_field=cli_field or yaml_filter.filter_field or "doi",
                batch_size=yaml_filter.batch_size,
                fallback_mapping=direct_fallback_mapping,
            )

        if not FilterConfigBuilder._is_filter_enabled(yaml_filter, cli_csv, test_mode):
            return None

        effective_csv = cli_csv or yaml_filter.source_path
        if not effective_csv:
            return None

        # Multi-column mode: use YAML config as-is
        if yaml_filter.columns and not cli_csv:
            return FilterConfigBuilder._build_multi_column_config(
                yaml_filter, effective_csv
            )

        # Single-column mode: CLI > YAML config
        return FilterConfigBuilder._build_single_column_config(
            yaml_filter, effective_csv, cli_column, cli_field, cli_fallback_column
        )

================================================================================
File: entrypoints.py
Path: entrypoints.py
================================================================================
"""Entrypoints for BioETL pipeline operations.

Provides high-level functions for running pipelines and managing resources.
These entrypoints are designed to be used by CLI, REST APIs, or any other
orchestration layer without direct dependency on bootstrap functions.

This module provides the unified pipeline execution interface (REQ-ARCH-041).
Any orchestration layer should use these entrypoints instead of bootstrap.

Split into submodules per audit-package-structure-2026-02-07:
- _pipeline_execution: Core pipeline build/run functions
- _resource_management: Legacy managers, maintenance, inspection
- _services: Application and infrastructure service factories
"""

from __future__ import annotations

# Re-export canonical DTO classes from application.services (H1 refactoring)
# These are the single source of truth for pipeline execution interfaces.
from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
from bioetl.composition._pipeline_execution import (
    ArchiveOptions,
    VacuumOptions,
    build_pipeline_context,
    create_pipeline_runner,
    ensure_metrics_server_started,
    run_pipeline,
)
from bioetl.composition._resource_management import (
    archive_table,
    get_checkpoint_manager,
    get_lifecycle_service,
    get_quarantine_manager,
    inspect_quarantine,
    list_checkpoints,
    preview_cleanup,
    vacuum_table,
)
from bioetl.composition._services import (
    cleanup_bronze,
    get_bronze_cleanup_service,
    get_checkpoint_service,
    get_config_service,
    get_export_service,
    get_health_server_dependencies,
    get_health_service,
    get_lock_service,
    get_metrics_service,
    get_pipeline_runner_service,
    get_quarantine_service,
    get_quarantine_store,
    get_vacuum_service,
)
from bioetl.composition.bootstrap import (
    load_pipeline_config,
    maybe_start_metrics_server,
)

__all__ = [
    # Configuration
    "load_pipeline_config",
    # Option classes (re-exported from application.services)
    "RunOptions",
    "VacuumOptions",
    "ArchiveOptions",
    # Result classes (re-exported from application.services)
    "RunResult",
    "PipelineRunResult",
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
    "get_export_service",
    "get_vacuum_service",
    # Maintenance operations
    "vacuum_table",
    "archive_table",
    "preview_cleanup",
    "cleanup_bronze",
    # Inspection
    "inspect_quarantine",
    "list_checkpoints",
    # Metrics server entrypoint
    "ensure_metrics_server_started",
    "maybe_start_metrics_server",
]

================================================================================
File: __init__.py
Path: factories\__init__.py
================================================================================
# src/bioetl/composition/factories/__init__.py
"""Pipeline factories module.

Provides the GenericPipelineFactory for creating pipeline instances declaratively.

Usage:
    >>> from bioetl.composition.factories import GenericPipelineFactory
    >>> factory = GenericPipelineFactory(...)

All pipeline factories are auto-registered when this module is imported.

Consolidated modules (v5.2):
- pipeline_factory: GenericPipelineFactory, runner assembly
- services_factory: BaseServicesFactory, ServicesBuilder
- data_source_factory: DataSourceFactory, DataSourceRegistry
- storage: StorageAdapter, StorageContext, StorageFactory
- dq_factory: DQServicesFactory for DQ report components
"""

# Data source factory and registry
from bioetl.composition.factories.data_source_factory import (
    DataSourceCreator,
    DataSourceFactory,
    DataSourceRegistry,
)

# DQ services factory
from bioetl.composition.factories.dq_factory import DQServicesFactory

# Import to trigger pipeline registration
from bioetl.composition.factories.pipeline_factories import (
    chembl_activity_factory,
    pubchem_compound_factory,
    pubmed_publication_factory,
    uniprot_protein_factory,
)

# Pipeline factory and runner assembly
from bioetl.composition.factories.pipeline_factory import (
    GenericPipelineFactory,
    assemble_runner,
    build_pipeline_services,
    create_pipeline_factory,
)

# Services factory (DI for PipelineRunner)
from bioetl.composition.factories.services_factory import (
    BaseServicesFactory,
    ServicesBuilder,
    create_data_normalization_service,
)

# Storage factory
from bioetl.composition.factories.storage import (
    StorageAdapter,
    StorageContext,
    StorageFactory,
)

# Transformer factory (DI for transformers)
from bioetl.composition.factories.transformer_factory import (
    create_transformer,
    get_transformer_class,
    register_all_transformers,
    register_transformer,
)

__all__ = [
    "BaseServicesFactory",
    "DQServicesFactory",
    "DataSourceCreator",
    "DataSourceFactory",
    "DataSourceRegistry",
    "GenericPipelineFactory",
    "ServicesBuilder",
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
    "assemble_runner",
    "build_pipeline_services",
    "chembl_activity_factory",
    "create_data_normalization_service",
    "create_pipeline_factory",
    "create_transformer",
    "get_transformer_class",
    "pubchem_compound_factory",
    "pubmed_publication_factory",
    "register_all_transformers",
    "register_transformer",
    "uniprot_protein_factory",
]

================================================================================
File: data_source_factory.py
Path: factories\data_source_factory.py
================================================================================
"""Data Source Factory and Registry.

Consolidated module for data source creation and registry.

Contains:
- DataSourceFactory: Abstract Factory for creating data source adapters
- DataSourceRegistry: Backward-compatible facade over ProviderRegistry

Usage:
    >>> from bioetl.composition.factories.data_source_factory import DataSourceFactory
    >>> adapter = DataSourceFactory.create("chembl", http_client=client, logger=logger)

After the registry unification, both classes delegate to ProviderRegistry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from bioetl.composition.providers import (
    DataSourceCreator,
    ProviderRegistry,
    ensure_providers_loaded,
)

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


# Re-export DataSourceCreator for backward compatibility
__all__ = ["DataSourceCreator", "DataSourceFactory", "DataSourceRegistry"]


class DataSourceFactory:
    """Factory for creating data source adapters.

    Uses ProviderRegistry for provider lookup and adapter creation.
    """

    @classmethod
    def create(
        cls,
        provider: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        **kwargs: Any,
    ) -> DataSourcePort:
        """Create a data source adapter.

        Uses ProviderRegistry for provider lookup and adapter creation.

        Args:
            provider: The name of the data provider (e.g., 'chembl', 'pubchem').
            http_client: The shared HTTP client to use (only for adapters that support it).
            logger: LoggerPort instance for structured logging.
            settings: Application settings (for custom creators).
            **kwargs: Additional keyword arguments to pass to the adapter constructor.

        Returns:
            An instance of the requested data source adapter.

        Raises:
            ValueError: If the provider is unknown.
        """
        # Ensure providers are loaded
        ensure_providers_loaded()

        # Validate provider is registered
        if not ProviderRegistry.is_registered(provider):
            available = ", ".join(ProviderRegistry.list_providers())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        # Remove filter_config from kwargs - it's handled by FilteredDataSource wrapper
        adapter_kwargs = {k: v for k, v in kwargs.items() if k != "filter_config"}

        return ProviderRegistry.create_adapter(
            provider,
            http_client=http_client,
            logger=logger,
            settings=settings,
            **adapter_kwargs,
        )

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all available providers.

        Returns:
            Sorted list of registered provider names.
        """
        ensure_providers_loaded()
        return ProviderRegistry.list_providers()


class DataSourceRegistry:
    """Thin facade over ProviderRegistry for data source creation.

    This class provides backward compatibility for code that used the old
    DataSourceRegistry API. It now delegates to ProviderRegistry for all
    operations.

    Example:
        >>> # Old way (still works)
        >>> creator = DataSourceRegistry.get("chembl")
        >>> data_source = creator(settings, pipeline_config, logger)
        >>>
        >>> # Preferred new way
        >>> data_source = ProviderRegistry.create_data_source(
        ...     "chembl", settings, pipeline_config, logger
        ... )

    Note:
        For new code, prefer using ProviderRegistry.create_data_source() directly.
    """

    # Empty dict - we delegate everything to ProviderRegistry
    _creators: ClassVar[dict[str, DataSourceCreator]] = {}

    @classmethod
    def get(cls, provider: str) -> DataSourceCreator:
        """Get creator function for provider.

        Returns a closure that delegates to ProviderRegistry.create_data_source().

        Args:
            provider: Provider name (e.g., 'chembl', 'pubchem')

        Returns:
            Creator function for the provider

        Raises:
            KeyError: If provider is not registered
        """
        ensure_providers_loaded()

        # Check if provider exists in ProviderRegistry
        if not ProviderRegistry.is_registered(provider):
            available = ", ".join(ProviderRegistry.list_providers())
            raise KeyError(f"Unknown provider: {provider}. Available: {available}")

        # Check if provider has data_source_creator configured
        if not ProviderRegistry.has_data_source_creator(provider):
            raise KeyError(
                f"Provider '{provider}' does not have a data_source_creator. "
                "Ensure it is registered with data_source_creator in registration.py."
            )

        # Return a closure that delegates to ProviderRegistry
        def creator(
            settings: Settings,
            pipeline_config: PipelineYamlConfig,
            logger: LoggerPort,
            filter_config: InputFilterConfig | None = None,
            metrics: MetricsPort | None = None,
            pipeline_name: str = "unknown",
        ) -> DataSourcePort:
            """Create a data source for the captured provider name.

            This closure captures the provider name from the outer scope and
            delegates creation to ProviderRegistry.create_data_source().

            Args:
                settings: Application settings for configuration.
                pipeline_config: Pipeline-specific YAML configuration.
                logger: LoggerPort for structured logging.
                filter_config: Optional input filtering configuration.
                metrics: Optional MetricsPort for observability.
                pipeline_name: Pipeline identifier for logging context.

            Returns:
                DataSourcePort implementation for the provider.

            Note:
                This is a backward-compatibility wrapper. For new code, prefer
                using ProviderRegistry.create_data_source() directly.
            """
            return ProviderRegistry.create_data_source(
                name=provider,
                settings=settings,
                pipeline_config=pipeline_config,
                logger=logger,
                filter_config=filter_config,
                metrics=metrics,
                pipeline_name=pipeline_name,
            )

        return creator

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered providers.

        Returns providers from ProviderRegistry that have data_source_creator.
        """
        ensure_providers_loaded()
        # Return all providers from ProviderRegistry
        # (they all have data_source_creator after unification)
        return ProviderRegistry.list_providers()

    @classmethod
    def list_keys(cls) -> list[str]:
        """List all registered provider names (unified API).

        Alias for list_providers().
        """
        return cls.list_providers()

    @classmethod
    def contains(cls, key: str) -> bool:
        """Check if provider is registered.

        Args:
            key: Provider name to check

        Returns:
            True if provider is registered and has data_source_creator
        """
        ensure_providers_loaded()
        return ProviderRegistry.has_data_source_creator(key)

    @classmethod
    def clear(cls) -> None:
        """Clear local registrations (for testing).

        Note: This only clears the local _creators dict.
        Use ProviderRegistry.clear() to clear the main registry.
        """
        cls._creators.clear()

================================================================================
File: dq_factory.py
Path: factories\dq_factory.py
================================================================================
"""Factory for DQ report components.

Creates DQ analyzers and report writers following the DI pattern.
All components are created in the composition layer and injected
into pipeline services.

Usage:
    >>> from bioetl.composition.factories.dq_factory import DQServicesFactory
    >>> analyzer = DQServicesFactory.create_bronze_analyzer()
    >>> writer = DQServicesFactory.create_report_writer(base_path, logger)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.dq import (
    BronzeDQAnalyzer,
    GoldDQAnalyzer,
    SilverDQAnalyzer,
)
from bioetl.infrastructure.export.dq_report_writer import DQReportWriter

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeDQAnalyzerPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        LoggerPort,
        SilverDQAnalyzerPort,
    )


class DQServicesFactory:
    """Factory for creating DQ analysis and reporting services.

    All methods are static factory methods following the composition pattern.
    Services are created lazily only when DQ reporting is enabled.

    Example:
        >>> factory = DQServicesFactory()
        >>> bronze_analyzer = DQServicesFactory.create_bronze_analyzer()
        >>> silver_analyzer = DQServicesFactory.create_silver_analyzer()
        >>> gold_analyzer = DQServicesFactory.create_gold_analyzer()
        >>> writer = DQServicesFactory.create_report_writer(Path("/data"), logger)
    """

    @staticmethod
    def create_bronze_analyzer() -> BronzeDQAnalyzerPort:
        """Create Bronze layer DQ analyzer.

        Returns:
            BronzeDQAnalyzerPort implementation for analyzing raw Bronze data.
        """
        return BronzeDQAnalyzer()

    @staticmethod
    def create_silver_analyzer() -> SilverDQAnalyzerPort:
        """Create Silver layer DQ analyzer.

        Returns:
            SilverDQAnalyzerPort implementation for analyzing normalized Silver data.
        """
        return SilverDQAnalyzer()

    @staticmethod
    def create_gold_analyzer() -> GoldDQAnalyzerPort:
        """Create Gold layer DQ analyzer.

        Returns:
            GoldDQAnalyzerPort implementation for analyzing Gold data marts.
        """
        return GoldDQAnalyzer()

    @staticmethod
    def create_report_writer(
        base_path: str | Path,
        logger: LoggerPort,
        flat_structure: bool = False,
    ) -> DQReportWriterPort:
        """Create DQ report writer.

        Args:
            base_path: Base path for report storage.
            logger: Structured logger for observability.
            flat_structure: If True, write reports directly to base_path
                          with {layer}_{provider}_{entity}_dq_report{ext} naming.

        Returns:
            DQReportWriterPort implementation for writing reports to filesystem.
        """
        return DQReportWriter(
            base_path=base_path,
            logger=logger,
            flat_structure=flat_structure,
        )


__all__ = ["DQServicesFactory"]

================================================================================
File: http_client_factory.py
Path: factories\http_client_factory.py
================================================================================
"""Factory for creating HTTP clients with standard configurations.

Ensures consistent rate limiting and circuit breaker settings across providers.
Uses source configuration from YAML files (configs/sources/*.yaml) for settings.

Configuration Priority:
1. Source YAML config (configs/sources/{provider}.yaml) - PRIMARY
2. Settings API key overrides (for rate limit boost with API keys)
3. ProviderRegistry defaults (fallback only)

SRP Compliance:
- Creates UnifiedHTTPClient with injected RateLimiterPort and CircuitBreakerPort
- RetryConfig is configured via domain value object
- Observability components (tracer, metrics, logger) are injected for correlation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.providers import ProviderRegistry, ensure_providers_loaded
from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.config import load_source_config

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings


class HttpClientFactory:
    """Factory for creating HTTP clients.

    Uses ProviderRegistry for configuration lookup.
    Injects observability components for distributed tracing and metrics.
    """

    @classmethod
    def create_for_provider(
        cls,
        provider: str,
        settings: Settings | None = None,
        *,
        run_id: RunID | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
    ) -> UnifiedHTTPClient:
        """Create a configured HTTP client for the given provider.

        Uses ProviderRegistry for configuration lookup.

        Args:
            provider: Provider name (e.g., 'chembl', 'pubmed')
            settings: Optional settings to override defaults (e.g., API keys)
            run_id: Optional run ID for correlation headers
            tracer: Optional TracingPort for distributed tracing
            metrics: Optional MetricsPort for metrics collection
            logger: Optional LoggerPort for structured logging

        Returns:
            UnifiedHTTPClient configured for the provider with observability

        Raises:
            ValueError: If the provider is unknown.
        """
        # Ensure providers are loaded
        ensure_providers_loaded()

        # Validate provider is registered
        if not ProviderRegistry.is_registered(provider):
            available = ", ".join(ProviderRegistry.list_providers())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        return cls._create_from_registry(
            provider,
            settings,
            run_id=run_id,
            tracer=tracer,
            metrics=metrics,
            logger=logger,
        )

    @classmethod
    def _create_from_registry(
        cls,
        provider: str,
        settings: Settings | None,
        *,
        run_id: RunID | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
    ) -> UnifiedHTTPClient:
        """Create HTTP client using source YAML configuration.

        Configuration is loaded from configs/sources/{provider}.yaml.
        Falls back to ProviderRegistry defaults if source config not found.

        Args:
            provider: Provider name
            settings: Application settings
            run_id: Optional run ID for correlation headers
            tracer: Optional TracingPort for distributed tracing
            metrics: Optional MetricsPort for metrics collection
            logger: Optional LoggerPort for structured logging

        Returns:
            Configured UnifiedHTTPClient with observability
        """
        # Load source config from YAML (primary source) if exists
        from pathlib import Path

        config_path = Path(f"configs/sources/{provider}.yaml")
        source_config = load_source_config(provider) if config_path.exists() else None

        # Get rate limit, circuit breaker, and client settings
        if source_config is not None:
            # Use source YAML config (primary)
            rate = source_config.rate_limit.requests_per_second
            capacity = source_config.rate_limit.burst
            failure_threshold = source_config.circuit_breaker.failure_threshold
            recovery_timeout = source_config.circuit_breaker.recovery_timeout
            # Client settings (timeout and retries)
            timeout = source_config.timeout_sec
            max_retries = source_config.max_retries
            base_delay = source_config.retry_base_delay
            max_delay = source_config.retry_max_delay
        else:
            # Fallback to ProviderRegistry
            http_config = ProviderRegistry.get_http_config(provider)
            if http_config is None:
                # Provider doesn't use shared HTTP client - use safe defaults
                rate = 5.0
                capacity = 10
                failure_threshold = 5
                recovery_timeout = 300
                timeout = 30.0
                max_retries = 3
            else:
                rate = http_config.rate
                capacity = http_config.capacity
                failure_threshold = 5  # Default
                recovery_timeout = 300  # Default
                timeout = 30.0  # Default
                max_retries = 3  # Default
            base_delay = 1.0  # RetryConfig default
            max_delay = 60.0  # RetryConfig default

        # Apply rate overrides based on settings (API key boosts)
        http_config = ProviderRegistry.get_http_config(provider)
        if settings and http_config and http_config.rate_overrides:
            for setting_name, override_rate in http_config.rate_overrides.items():
                if cls._check_setting(settings, setting_name):
                    rate = override_rate
                    capacity = int(override_rate * 2)
                    break

        return UnifiedHTTPClient(
            rate_limiter=TokenBucket(rate=rate, capacity=capacity, provider=provider),
            circuit_breaker=CircuitBreaker(
                provider=provider,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                metrics=metrics,
            ),
            retry_config=RetryConfig(
                max_attempts=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
            ),
            timeout=timeout,
            provider=provider,
            run_id=run_id,
            tracer=tracer,
            metrics=metrics,
            logger=logger,
        )

    @classmethod
    def _check_setting(cls, settings: Settings, setting_name: str) -> bool:
        """Check if a setting is present and truthy.

        Args:
            settings: Application settings
            setting_name: Name of the setting to check

        Returns:
            True if setting exists and is truthy
        """
        value = getattr(settings, setting_name, None)
        return value is not None and bool(value)

================================================================================
File: pipeline_factories.py
Path: factories\pipeline_factories.py
================================================================================
# src/bioetl/composition/factories/pipeline_factories.py
"""Consolidated pipeline factory definitions.

This module creates all pipeline factories using the GenericPipelineFactory
pattern with GenericPipeline as the unified pipeline class.

All pipeline-specific behavior is encapsulated in:
- YAML configs (configs/pipelines/{provider}/{entity}.yaml)
- Transformer classes (injected via DI)
- Silver/Gold schemas

Thread-safety: Registration uses a module-level lock to prevent TOCTOU race conditions.

Instance-level registry support (2025-12):
- register_all_pipelines() accepts optional registry parameter
- Default behavior uses global registry for backward compatibility
- Tests can use isolated registries for parallel execution

Refactored (2025-12):
- All pipelines now use GenericPipeline instead of provider-specific subclasses
- Pipeline definitions consolidated into PIPELINE_CONFIGS for loop-based registration
- Document → Publication naming unified (ADR-024)

Usage:
    >>> from bioetl.composition.factories.pipeline_factories import register_all_pipelines
    >>> register_all_pipelines()  # Call once at application startup

    # For test isolation:
    >>> from bioetl.composition.registry import create_registry
    >>> registry = create_registry()
    >>> register_all_pipelines(registry=registry)
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, NamedTuple

# Transformers (all DI-injected)
from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer
from bioetl.application.pipelines.chembl.assay_parameters_transformer import (
    AssayParametersTransformer,
)
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.cell_line_transformer import (
    CellLineTransformer,
)
from bioetl.application.pipelines.chembl.compound_record_transformer import (
    CompoundRecordTransformer,
)
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.application.pipelines.chembl.protein_class_transformer import (
    ProteinClassTransformer,
)
from bioetl.application.pipelines.chembl.publication_similarity_transformer import (
    PublicationSimilarityTransformer,
)
from bioetl.application.pipelines.chembl.publication_term_transformer import (
    PublicationTermTransformer,
)
from bioetl.application.pipelines.chembl.publication_transformer import (
    PublicationTransformer,
)
from bioetl.application.pipelines.chembl.subcellular_fraction_transformer import (
    SubcellularFractionTransformer,
)
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.chembl.tissue_transformer import TissueTransformer
from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)
from bioetl.application.pipelines.generic import GenericPipeline
from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexPublicationTransformer,
)
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.application.pipelines.semanticscholar.transformer import (
    SemanticScholarPublicationTransformer,
)
from bioetl.application.pipelines.uniprot.idmapping_transformer import (
    IDMappingTransformer,
)
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from bioetl.composition.factories.data_source_factory import DataSourceRegistry
from bioetl.composition.factories.pipeline_factory import GenericPipelineFactory
from bioetl.composition.registry import PipelineRegistry, get_default_registry

# Gold schemas (required for all pipelines)
# Imported from domain.contracts package for clean separation of data contracts
from bioetl.domain.contracts import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLDocumentGoldSchema,
    ChEMBLDocumentSimilarityGoldSchema,
    ChEMBLDocumentTermGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLSubcellularFractionGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    ChEMBLTissueGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)

# Pandera Silver schemas (DataFrameModel classes for validation)
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema
from bioetl.domain.schemas.chembl.compound_record import CompoundRecordSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.protein_classification import (
    ProteinClassificationSchema,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.chembl.publication_similarity import (
    PublicationSimilaritySchema,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.pubchem.compound import PubchemMoleculeSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema
from bioetl.domain.schemas.uniprot.protein import UniprotTargetSchema

# Silver schemas (optional PyArrow schemas)
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_PARAMETERS_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_CELL_LINE_SCHEMA,
    CHEMBL_COMPOUND_RECORD_SCHEMA,
    CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
    CHEMBL_DOCUMENT_TERM_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_PROTEIN_CLASS_SCHEMA,
    CHEMBL_PUBLICATION_SCHEMA,
    CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    CHEMBL_TISSUE_SCHEMA,
    CROSSREF_PUBLICATION_SCHEMA,
    OPENALEX_PUBLICATION_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    UNIPROT_ID_MAPPING_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.composition.factories.data_source_factory import DataSourceCreator


# =============================================================================
# Pipeline Configuration Registry
# =============================================================================


class PipelineFactoryConfig(NamedTuple):
    """Configuration for creating a pipeline factory.

    This is a value object that holds all metadata needed to create a
    GenericPipelineFactory instance.

    Attributes:
        pipeline_name: Unique identifier for the pipeline (e.g., "chembl_activity")
        provider: Data provider name (e.g., "chembl", "pubchem").
            Used for transformer metadata (content hash, entity ID, tracing).
        transformer_class: Transformer class for Bronze→Silver transformation
        silver_schema: PyArrow schema for Silver layer validation
        gold_schema: Pandera schema for Gold layer validation (required)
        pandera_silver_schema: Pandera DataFrameModel class for Silver validation.
            If provided, PanderaSilverValidator is created and injected into
            SilverWriter for pre-write validation.
        data_source_provider: Override provider name for DataSourceRegistry lookup.
            When set, data source is created using this provider name instead of
            ``provider``. Use when the ProviderRegistry key differs from the
            transformer provider (e.g., "uniprot_idmapping" vs "uniprot").
    """

    pipeline_name: str
    provider: str
    transformer_class: type[BaseTransformer]
    silver_schema: pa.Schema | None
    gold_schema: Any  # Pandera schema class
    pandera_silver_schema: Any = None  # Pandera DataFrameModel class
    data_source_provider: str | None = None


# Consolidated pipeline definitions - single source of truth
PIPELINE_CONFIGS: tuple[PipelineFactoryConfig, ...] = (
    # ChEMBL pipelines
    PipelineFactoryConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        transformer_class=ActivityTransformer,
        silver_schema=CHEMBL_ACTIVITY_SCHEMA,
        gold_schema=ChEMBLActivityGoldSchema,
        pandera_silver_schema=ActivitySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_assay",
        provider="chembl",
        transformer_class=AssayTransformer,
        silver_schema=CHEMBL_ASSAY_SCHEMA,
        gold_schema=ChEMBLAssayGoldSchema,
        pandera_silver_schema=AssaySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_assay_parameters",
        provider="chembl",
        transformer_class=AssayParametersTransformer,
        silver_schema=CHEMBL_ASSAY_PARAMETERS_SCHEMA,
        gold_schema=ChEMBLAssayParametersGoldSchema,
        pandera_silver_schema=AssayParametersSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_cell_line",
        provider="chembl",
        transformer_class=CellLineTransformer,
        silver_schema=CHEMBL_CELL_LINE_SCHEMA,
        gold_schema=ChEMBLCellLineGoldSchema,
        pandera_silver_schema=CellLineSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_compound_record",
        provider="chembl",
        transformer_class=CompoundRecordTransformer,
        silver_schema=CHEMBL_COMPOUND_RECORD_SCHEMA,
        gold_schema=ChEMBLCompoundRecordGoldSchema,
        pandera_silver_schema=CompoundRecordSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication",
        provider="chembl",
        transformer_class=PublicationTransformer,
        silver_schema=CHEMBL_PUBLICATION_SCHEMA,
        gold_schema=ChEMBLDocumentGoldSchema,
        pandera_silver_schema=ChemblPublicationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication_similarity",
        provider="chembl",
        transformer_class=PublicationSimilarityTransformer,
        silver_schema=CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
        gold_schema=ChEMBLDocumentSimilarityGoldSchema,
        pandera_silver_schema=PublicationSimilaritySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication_term",
        provider="chembl",
        transformer_class=PublicationTermTransformer,
        silver_schema=CHEMBL_DOCUMENT_TERM_SCHEMA,
        gold_schema=ChEMBLDocumentTermGoldSchema,
        pandera_silver_schema=PublicationTermSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_molecule",
        provider="chembl",
        transformer_class=MoleculeTransformer,
        silver_schema=CHEMBL_MOLECULE_SCHEMA,
        gold_schema=ChEMBLMoleculeGoldSchema,
        pandera_silver_schema=MoleculeSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_target",
        provider="chembl",
        transformer_class=TargetTransformer,
        silver_schema=CHEMBL_TARGET_SCHEMA,
        gold_schema=ChEMBLTargetGoldSchema,
        pandera_silver_schema=TargetSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_target_component",
        provider="chembl",
        transformer_class=TargetComponentTransformer,
        silver_schema=CHEMBL_TARGET_COMPONENT_SCHEMA,
        gold_schema=ChEMBLTargetComponentGoldSchema,
        pandera_silver_schema=TargetComponentSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_protein_class",
        provider="chembl",
        transformer_class=ProteinClassTransformer,
        silver_schema=CHEMBL_PROTEIN_CLASS_SCHEMA,
        gold_schema=ChEMBLProteinClassGoldSchema,
        pandera_silver_schema=ProteinClassificationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_tissue",
        provider="chembl",
        transformer_class=TissueTransformer,
        silver_schema=CHEMBL_TISSUE_SCHEMA,
        gold_schema=ChEMBLTissueGoldSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_subcellular_fraction",
        provider="chembl",
        transformer_class=SubcellularFractionTransformer,
        silver_schema=CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
        gold_schema=ChEMBLSubcellularFractionGoldSchema,
    ),
    # PubChem pipeline
    PipelineFactoryConfig(
        pipeline_name="pubchem_compound",
        provider="pubchem",
        transformer_class=PubChemCompoundTransformer,
        silver_schema=PUBCHEM_COMPOUND_SCHEMA,
        gold_schema=PubChemCompoundGoldSchema,
        pandera_silver_schema=PubchemMoleculeSchema,
    ),
    # UniProt pipelines
    PipelineFactoryConfig(
        pipeline_name="uniprot_protein",
        provider="uniprot",
        transformer_class=UniProtProteinTransformer,
        silver_schema=UNIPROT_PROTEIN_SCHEMA,
        gold_schema=UniProtProteinGoldSchema,
        pandera_silver_schema=UniprotTargetSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="uniprot_idmapping",
        provider="uniprot",
        transformer_class=IDMappingTransformer,
        silver_schema=UNIPROT_ID_MAPPING_SCHEMA,
        gold_schema=UniProtIDMappingGoldSchema,
        pandera_silver_schema=IDMappingSchema,
        data_source_provider="uniprot_idmapping",
    ),
    # PubMed pipeline
    PipelineFactoryConfig(
        pipeline_name="pubmed_publication",
        provider="pubmed",
        transformer_class=PubMedPublicationTransformer,
        silver_schema=PUBMED_PUBLICATION_SCHEMA,
        gold_schema=PubMedPublicationGoldSchema,
        pandera_silver_schema=PubMedPublicationSchema,
    ),
    # CrossRef pipeline
    PipelineFactoryConfig(
        pipeline_name="crossref_publication",
        provider="crossref",
        transformer_class=CrossRefPublicationTransformer,
        silver_schema=CROSSREF_PUBLICATION_SCHEMA,
        gold_schema=CrossRefPublicationGoldSchema,
        pandera_silver_schema=PublicationEnrichedSchema,
    ),
    # OpenAlex pipeline
    PipelineFactoryConfig(
        pipeline_name="openalex_publication",
        provider="openalex",
        transformer_class=OpenAlexPublicationTransformer,
        silver_schema=OPENALEX_PUBLICATION_SCHEMA,
        gold_schema=OpenAlexPublicationGoldSchema,
        pandera_silver_schema=OpenAlexPublicationSchema,
    ),
    # Semantic Scholar pipeline
    PipelineFactoryConfig(
        pipeline_name="semanticscholar_publication",
        provider="semanticscholar",
        transformer_class=SemanticScholarPublicationTransformer,
        silver_schema=SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
        gold_schema=SemanticScholarPublicationGoldSchema,
        pandera_silver_schema=SemanticScholarPublicationSchema,
    ),
)


def _create_factory(
    config: PipelineFactoryConfig,
) -> GenericPipelineFactory[GenericPipeline]:
    """Create a GenericPipelineFactory from configuration.

    Args:
        config: Pipeline factory configuration

    Returns:
        Configured GenericPipelineFactory instance
    """
    # Resolve data source creator: use data_source_provider override if set
    data_source_creator: DataSourceCreator | None = None
    if config.data_source_provider:
        data_source_creator = DataSourceRegistry.get(config.data_source_provider)

    return GenericPipelineFactory(
        pipeline_name=config.pipeline_name,
        pipeline_class=GenericPipeline,
        provider=config.provider,
        silver_schema=config.silver_schema,
        gold_schema=config.gold_schema,
        pandera_silver_schema=config.pandera_silver_schema,
        transformer_class=config.transformer_class,
        data_source_creator=data_source_creator,
    )


# =============================================================================
# Factory Instances (created from PIPELINE_CONFIGS)
# =============================================================================

# Create all factories using loop over configurations
_factories: dict[str, GenericPipelineFactory[GenericPipeline]] = {
    config.pipeline_name: _create_factory(config) for config in PIPELINE_CONFIGS
}

# Export individual factories for backward compatibility
chembl_activity_factory = _factories["chembl_activity"]
chembl_assay_factory = _factories["chembl_assay"]
chembl_assay_parameters_factory = _factories["chembl_assay_parameters"]
chembl_cell_line_factory = _factories["chembl_cell_line"]
chembl_compound_record_factory = _factories["chembl_compound_record"]
chembl_publication_factory = _factories["chembl_publication"]
chembl_publication_similarity_factory = _factories["chembl_publication_similarity"]
chembl_publication_term_factory = _factories["chembl_publication_term"]
chembl_molecule_factory = _factories["chembl_molecule"]
chembl_target_factory = _factories["chembl_target"]
chembl_target_component_factory = _factories["chembl_target_component"]
chembl_tissue_factory = _factories["chembl_tissue"]
chembl_subcellular_fraction_factory = _factories["chembl_subcellular_fraction"]
chembl_protein_class_factory = _factories["chembl_protein_class"]
pubchem_compound_factory = _factories["pubchem_compound"]
uniprot_protein_factory = _factories["uniprot_protein"]
uniprot_idmapping_factory = _factories["uniprot_idmapping"]
pubmed_publication_factory = _factories["pubmed_publication"]
crossref_publication_factory = _factories["crossref_publication"]
openalex_publication_factory = _factories["openalex_publication"]
semanticscholar_publication_factory = _factories["semanticscholar_publication"]


# =============================================================================
# Registration Functions
# =============================================================================

# Thread-safe registration state
_registration_lock = threading.Lock()
_factories_registered = False


def register_all_pipelines(registry: PipelineRegistry | None = None) -> None:
    """Explicitly register all pipeline factories with PipelineRegistry.

    This function is idempotent and thread-safe - calling it multiple times
    or from multiple threads has no effect after the first successful call.

    Uses double-checked locking pattern to minimize lock contention while
    ensuring thread-safe initialization.

    When called with a custom registry, idempotency check is skipped
    (each registry instance is independent).

    Args:
        registry: Optional PipelineRegistry instance. If None, uses the
            default global registry. Pass a custom registry for test isolation.

    Should be called once at application startup (e.g., in cli.py or bootstrap.py).
    """
    global _factories_registered

    # For custom registries, register directly without idempotency check
    if registry is not None:
        _register_factories_to(registry)
        return

    # Default registry: use idempotency guard
    # Fast path: already registered (no lock needed)
    if _factories_registered:
        return

    # Slow path: acquire lock and double-check
    with _registration_lock:
        # Double-check after acquiring lock (TOCTOU prevention)
        if _factories_registered:
            return

        default_registry = get_default_registry()
        _register_factories_to(default_registry)

        _factories_registered = True


def _register_factories_to(registry: PipelineRegistry) -> None:
    """Register all factory instances to the given registry.

    Internal helper for register_all_pipelines().
    Uses loop over _factories dict for DRY registration.

    Args:
        registry: Target registry instance.
    """
    for factory in _factories.values():
        registry.register_factory(factory)


def is_registered() -> bool:
    """Check if factories have been registered.

    Thread-safe check of registration state.

    Returns:
        True if register_all_pipelines() has been called.
    """
    # Reading a bool is atomic in Python, no lock needed for read
    return _factories_registered


def reset_registration() -> None:
    """Reset registration state (for testing only).

    Thread-safe reset of registration flag. Also clears the default PipelineRegistry.
    WARNING: Only use in tests. Not for production.

    Note: For isolated tests, prefer creating a new registry instance with
    create_registry() rather than using reset_registration().
    """
    global _factories_registered
    with _registration_lock:
        get_default_registry().clear()
        _factories_registered = False


def get_factory(pipeline_name: str) -> GenericPipelineFactory[GenericPipeline]:
    """Get a pipeline factory by name.

    Convenience function for accessing factories without going through registry.

    Args:
        pipeline_name: Name of the pipeline (e.g., "chembl_activity")

    Returns:
        GenericPipelineFactory instance

    Raises:
        KeyError: If pipeline_name is not found
    """
    if pipeline_name not in _factories:
        available = sorted(_factories.keys())
        raise KeyError(f"Unknown pipeline: {pipeline_name}. Available: {available}")
    return _factories[pipeline_name]


def list_available_pipelines() -> list[str]:
    """List all available pipeline names.

    Returns:
        Sorted list of pipeline names
    """
    return sorted(_factories.keys())


_PIPELINE_FACTORY_API = (
    get_factory,
    list_available_pipelines,
    reset_registration,
)

__all__ = [
    "PIPELINE_CONFIGS",
    "PipelineFactoryConfig",
    "chembl_activity_factory",
    "chembl_assay_factory",
    "chembl_assay_parameters_factory",
    "chembl_cell_line_factory",
    "chembl_compound_record_factory",
    "chembl_molecule_factory",
    "chembl_protein_class_factory",
    "chembl_publication_factory",
    "chembl_publication_similarity_factory",
    "chembl_publication_term_factory",
    "chembl_subcellular_fraction_factory",
    "chembl_target_component_factory",
    "chembl_target_factory",
    "chembl_tissue_factory",
    "crossref_publication_factory",
    "get_factory",
    "is_registered",
    "list_available_pipelines",
    "openalex_publication_factory",
    "pubchem_compound_factory",
    "pubmed_publication_factory",
    "register_all_pipelines",
    "reset_registration",
    "semanticscholar_publication_factory",
    "uniprot_idmapping_factory",
    "uniprot_protein_factory",
]

================================================================================
File: pipeline_factory.py
Path: factories\pipeline_factory.py
================================================================================
"""Pipeline Factory - consolidated module for pipeline and runner creation.

Contains GenericPipelineFactory, assemble_runner, build_pipeline_services,
and create_pipeline_with_services. Follows DI pattern with declarative
configuration and assembly in the composition layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.postrun_service import PostrunService
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.composition.bootstrap_contexts import DQConfigsContext, DQOutputPathsContext
from bioetl.composition.factories.data_source_factory import (
    DataSourceCreator,
    DataSourceRegistry,
)
from bioetl.composition.factories.services_factory import (
    BaseServicesFactory,
    ServicesBuilder,
)
from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.locking import LockContextHolder
from bioetl.domain.medallion import LoadingStrategy
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain
from bioetl.infrastructure.config.pipeline_config_loader import ConfigLoader

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import (
        GoldFilterConfig,
        InputFilterConfig,
        SilverFilterConfig,
    )
    from bioetl.domain.ports import (
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.services import IdentityService
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")


__all__ = [
    "GenericPipelineFactory",
    "assemble_runner",
    "build_pipeline_services",
    "create_pipeline_factory",
    "create_pipeline_with_services",
]


def _extract_entity_type(pipeline_name: str) -> str | None:
    """Extract entity_type from pipeline_name.

    Example: "chembl_activity" → "activity"

    Args:
        pipeline_name: Full pipeline name with provider prefix.

    Returns:
        Entity type suffix, or None if no underscore in name.
    """
    return pipeline_name.split("_")[-1] if "_" in pipeline_name else None


# =============================================================================
# GenericPipelineFactory - Main factory class
# =============================================================================


class GenericPipelineFactory(Generic[TPipeline]):
    """Configurable factory for creating pipelines via constructor parameters.

    Attributes:
        pipeline_name: Unique name for the pipeline
        pipeline_class: The pipeline class to instantiate
        silver_schema: PyArrow schema for Silver layer
        gold_schema: Pandera schema for Gold layer
        pandera_silver_schema: Pandera DataFrameModel class for Silver validation
    """

    def __init__(
        self,
        pipeline_name: str,
        pipeline_class: type[TPipeline],
        provider: str,
        silver_schema: pa.Schema | None = None,
        gold_schema: Any = None,
        pandera_silver_schema: Any = None,
        data_source_creator: DataSourceCreator | None = None,
        transformer_class: type[BaseTransformer] | None = None,
    ) -> None:
        """Initialize the factory.

        Raises:
            ValueError: If gold_schema is not provided
        """
        if gold_schema is None:
            raise ValueError(
                f"gold_schema is required for pipeline '{pipeline_name}'. "
                "All Gold layer writes must have schema validation."
            )
        self.pipeline_name = pipeline_name
        self.pipeline_class = pipeline_class
        self.provider = provider
        self.silver_schema = silver_schema
        self.gold_schema = gold_schema
        self.pandera_silver_schema = pandera_silver_schema
        self.transformer_class = transformer_class

        # Use custom creator or look up from registry
        self._create_data_source = data_source_creator or DataSourceRegistry.get(
            provider
        )

    def create_transformer(
        self,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | GoldFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
    ) -> BaseTransformer | None:
        """Create transformer instance if transformer_class is configured.

        Args:
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            silver_filters: Optional domain-level filter configuration for Silver layer.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names.

        Returns:
            Configured transformer instance, or None if no transformer_class.
        """
        if self.transformer_class is None:
            return None

        return self.transformer_class(
            provider=self.provider,
            entity_type=_extract_entity_type(self.pipeline_name),
            tracer=tracer,
            metrics=metrics,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
        )

    def create_data_source(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create data source using the configured creator."""
        return self._create_data_source(
            settings,
            pipeline_config,
            logger,
            filter_config,
            pipeline_name=self.pipeline_name,
        )

    def build_services(
        self,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
    ) -> PipelineServices:
        """Build PipelineServices from settings."""
        return build_pipeline_services(
            pipeline_name=self.pipeline_name,
            create_data_source_fn=self._create_data_source,
            settings=settings,
            logger=logger,
            config=config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
        )

    def create_with_services(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metrics: MetricsPort | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> TPipeline:
        """Create pipeline instance with services and optional transformer."""
        return cast(
            TPipeline,
            create_pipeline_with_services(
                pipeline_name=self.pipeline_name,
                pipeline_class=self.pipeline_class,
                provider=self.provider,
                create_data_source_fn=self._create_data_source,
                transformer_class=self.transformer_class,
                pandera_silver_schema=self.pandera_silver_schema,
                run_id=run_id,
                runtime=runtime,
                settings=settings,
                logger=logger,
                config=config,
                filter_config=filter_config,
                tracer=tracer,
                dq_monitor=dq_monitor,
                metrics=metrics,
                cached_bronze=cached_bronze,
            ),
        )

    def create_runner(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        observability: ObservabilityBundle,
        filter_config: InputFilterConfig | None = None,
        config: PipelineYamlConfig | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> PipelineRunner:
        """Create a fully configured PipelineRunner with all components."""
        # Load config once if not provided
        yaml_config = config or load_pipeline_config(self.pipeline_name)

        # Create pipeline instance with services, tracer, metrics, and dq_monitor (O1)
        # Cast logger to LoggerPort - structlog.BoundLogger is runtime-compatible
        pipeline = self.create_with_services(
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            logger=observability.logger,
            config=yaml_config,
            filter_config=filter_config,
            tracer=observability.tracer,
            dq_monitor=observability.dq_monitor,
            metrics=observability.metrics,
            cached_bronze=cached_bronze,
        )

        # Delegate runner assembly to dedicated function
        return assemble_runner(
            pipeline=pipeline,
            observability=observability,
            silver_schema=self.silver_schema,
            gold_schema=self.gold_schema,
            strict_gold_validation=runtime.strict_gold_validation,
            yaml_config=yaml_config,
        )


def create_pipeline_factory(
    pipeline_name: str,
    pipeline_class: type[TPipeline],
    provider: str,
    silver_schema: pa.Schema | None = None,
    gold_schema: Any = None,
    pandera_silver_schema: Any = None,
    transformer_class: type[BaseTransformer] | None = None,
) -> GenericPipelineFactory[TPipeline]:
    """Convenience function for creating pipeline factories."""
    return GenericPipelineFactory(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        pandera_silver_schema=pandera_silver_schema,
        transformer_class=transformer_class,
    )


# =============================================================================
# Runner Assembly Functions
# =============================================================================


def _create_data_source(
    create_data_source_fn: DataSourceCreator,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create data source using the provided creator function.

    Args:
        create_data_source_fn: Data source creator function
        settings: Application settings
        pipeline_config: Pipeline configuration
        logger: Structured logger
        filter_config: Optional filter configuration
        pipeline_name: Pipeline name for logging context

    Returns:
        Configured DataSourcePort
    """
    return create_data_source_fn(
        settings, pipeline_config, logger, filter_config, pipeline_name=pipeline_name
    )


def _create_cached_bronze_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    cached_bronze: CachedBronzeContext,
) -> DataSourcePort:
    """Create CachedBronzeDataSource for reading from Bronze cache.

    Creates a data source that reads from existing Bronze layer files
    instead of making API calls. Used when cached_bronze mode is enabled.

    Args:
        settings: Application settings (for resolving base paths).
        pipeline_config: Pipeline configuration (for provider/entity).
        logger: Structured logger.
        cached_bronze: CachedBronzeContext with path/date settings.

    Returns:
        CachedBronzeDataSource implementing DataSourcePort.
    """
    from pathlib import Path

    from bioetl.domain.ports import NoOpMetrics
    from bioetl.infrastructure.adapters import CachedBronzeDataSource
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

    provider = pipeline_config.provider
    entity_type = pipeline_config.entity_type

    # Resolve Bronze path: explicit or convention-based
    if cached_bronze.bronze_path:
        bronze_path = Path(cached_bronze.bronze_path)
    else:
        # Convention: data/output/bronze/{provider}/{entity_type}
        bronze_path = settings.bronze_path / provider / entity_type

    # Create BronzeWriter as reader (reusing read_bronze/list_batches methods)
    # flat_structure=True because convention path already includes provider/entity
    bronze_reader = BronzeWriter(
        base_path=bronze_path,
        logger=logger,
        metrics=NoOpMetrics(),
        flat_structure=True,
    )

    return CachedBronzeDataSource(
        bronze_reader=bronze_reader,
        provider=provider,
        entity_type=entity_type,
        logger=logger,
        bronze_date=cached_bronze.bronze_date,
    )


def build_pipeline_services(
    pipeline_name: str,
    create_data_source_fn: DataSourceCreator,
    settings: Settings,
    logger: LoggerPort,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metadata_coordinator: MetadataCoordinator | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    silver_validator: Any = None,
) -> PipelineServices:
    """Build PipelineServices from settings.

    Args:
        pipeline_name: Name of the pipeline for config lookup
        create_data_source_fn: Data source creator function
        settings: Application settings
        logger: Structured logger
        config: Pre-loaded pipeline config (avoids duplicate I/O)
        filter_config: Optional input filter configuration
        tracer: Optional tracer (created via bootstrap_tracer())
        dq_monitor: Optional data quality monitor for anomaly detection
        metadata_coordinator: Optional MetadataCoordinator for centralized
                            metadata creation across Bronze, Silver, Gold.
        cached_bronze: Optional CachedBronzeContext for reading from Bronze
                      cache instead of API. When enabled, creates
                      CachedBronzeDataSource instead of the normal data source.
        silver_validator: Optional SilverValidatorPort for Pandera validation
            in SilverWriter. Created from Pandera Silver schema.

    Returns:
        Configured PipelineServices instance
    """
    pipeline_config = config or load_pipeline_config(pipeline_name)

    # Choose data source based on cached_bronze mode
    if cached_bronze is not None and cached_bronze.enabled:
        data_source = _create_cached_bronze_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            cached_bronze=cached_bronze,
        )
        logger.info(
            "using_cached_bronze_mode",
            pipeline=pipeline_name,
            bronze_path=cached_bronze.bronze_path,
            bronze_date=cached_bronze.bronze_date,
        )
    else:
        data_source = _create_data_source(
            create_data_source_fn,
            settings,
            pipeline_config,
            logger,
            filter_config,
            pipeline_name=pipeline_name,
        )

    return BaseServicesFactory.create_common_services(
        settings=settings,
        logger=logger,
        data_source=data_source,
        pipeline_config=pipeline_config,
        tracer=tracer,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        silver_validator=silver_validator,
    )


def create_pipeline_with_services(
    pipeline_name: str,
    pipeline_class: type[BasePipeline],
    provider: str,
    create_data_source_fn: DataSourceCreator,
    transformer_class: type[BaseTransformer] | None,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metrics: MetricsPort | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    pandera_silver_schema: Any = None,
) -> BasePipeline:
    """Create pipeline instance with services.

    Loads config once and reuses it for both services and pipeline.
    If transformer_class is configured, creates and injects transformer via DI.

    Args:
        pipeline_name: Name of the pipeline
        pipeline_class: Pipeline class to instantiate
        provider: Data provider name
        create_data_source_fn: Data source creator function
        transformer_class: Optional transformer class for Bronze→Silver
        run_id: Unique identifier for this pipeline run
        runtime: Pipeline runtime configuration
        settings: Application settings
        logger: Structured logger
        config: Pre-loaded pipeline config (avoids duplicate I/O)
        filter_config: Optional input filter configuration
        tracer: Optional tracer for distributed tracing
        dq_monitor: Optional data quality monitor
        metrics: Optional metrics port for transformer observability
        cached_bronze: Optional CachedBronzeContext for reading from Bronze
                      cache instead of API.
        pandera_silver_schema: Optional Pandera DataFrameModel class for Silver
            validation. If provided, PanderaSilverValidator is created and
            injected into SilverWriter.

    Returns:
        Configured pipeline instance
    """
    yaml_config = config or load_pipeline_config(pipeline_name)
    entity = _extract_entity_type(pipeline_name) or pipeline_name

    # Create Silver validator from Pandera schema if provided (DI pattern)
    silver_validator = None
    if pandera_silver_schema is not None:
        from bioetl.infrastructure.validation.pandera_validator import (
            PanderaSilverValidator,
        )

        silver_validator = PanderaSilverValidator(pandera_silver_schema.to_schema())

    # Create RunContext with versioning metadata for MetadataCoordinator
    run_context = RunContext.create(
        run_id=run_id,
        run_type=runtime.run_type,
        started_at=datetime.now(UTC),
        provider=provider,
        entity=entity,
        pipeline_version=get_pipeline_version(yaml_config),
        git_commit=get_git_commit(),
        config_hash=compute_config_hash(yaml_config),
    )
    metadata_coordinator = MetadataCoordinator(run_context)

    services = build_pipeline_services(
        pipeline_name=pipeline_name,
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        logger=logger,
        config=yaml_config,
        filter_config=filter_config,
        tracer=tracer,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        cached_bronze=cached_bronze,
        silver_validator=silver_validator,
    )

    config_loader = ConfigLoader(
        Path("configs"), relaxed_dq=settings.pipeline.relaxed_dq
    )
    resolved_dq = config_loader.resolve_dq_config(yaml_config)
    domain_config = yaml_config_to_domain(yaml_config, resolved_dq_config=resolved_dq)

    # Create transformer via DI if configured (with observability)
    transformer = None
    if transformer_class is not None:
        transformer = transformer_class(
            provider=provider,
            entity_type=_extract_entity_type(pipeline_name),
            tracer=tracer,
            metrics=metrics,
            silver_filters=domain_config.silver_filters,
            gold_filters=domain_config.gold_filters,
            # identity_service and pii_hasher use defaults in transformer
        )

    return pipeline_class.create(
        run_id=run_id,
        runtime=runtime,
        services=services,
        config=domain_config,
        transformer=transformer,
    )


def assemble_runner(
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    silver_schema: pa.Schema | None,
    gold_schema: Any,
    strict_gold_validation: bool,
    yaml_config: PipelineYamlConfig | None = None,
) -> PipelineRunner:
    """Assemble a PipelineRunner from a pipeline instance.

    This function handles the construction of the entire pipeline execution graph,
    using the unified BatchExecutor that combines extraction and processing.

    All services are created directly here (DI pattern) instead of through
    an intermediate RunnerServices bundle for explicit dependency injection.

    Args:
        pipeline: Configured pipeline instance
        observability: Unified observability bundle (logger, tracer, metrics, dq_monitor)
        silver_schema: PyArrow schema for Silver layer
        gold_schema: Schema for Gold layer validation
        strict_gold_validation: Whether to enforce strict Gold validation
        yaml_config: Original YAML config for DQ report extraction

    Returns:
        Fully initialized PipelineRunner
    """
    # Create Helper Components using ServicesBuilder
    logger_port = observability.logger

    # Cast loading_strategy since __post_init__ converts str to LoadingStrategy enum
    checkpoint_manager = ServicesBuilder.create_checkpoint_manager(
        checkpoint_port=pipeline.services.checkpoint,
        logger=logger_port,
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.run_id,
        resume=pipeline.runtime.resume,
        loading_strategy=cast(LoadingStrategy | None, pipeline.config.loading_strategy),
    )

    # Create lifecycle service (M5)
    lifecycle_service = MedallionLifecycleService(
        storage=pipeline.services.storage,
        logger=logger_port,
    )

    # Create shared LockContextHolder to pass context from LockManager to RecordProcessor
    context_holder = LockContextHolder()

    # Create application services directly (DI pattern, no intermediate bundle)
    lock_manager = LockManager.create(
        lock_port=pipeline.services.lock,
        run_id=pipeline.context.run_id,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        run_type=pipeline.runtime.run_type,
        lock_ttl=pipeline.runtime.effective_lock_ttl,
        wait_for_lock=pipeline.runtime.wait_for_lock,
        wait_timeout=pipeline.runtime.lock_wait_timeout,
        heartbeat_interval=pipeline.runtime.heartbeat_interval,
        logger=logger_port,
        shutdown_signal=pipeline.shutdown_signal,
        checkpoint_manager=checkpoint_manager,
        context_holder=context_holder,
    )

    preflight_service = PreflightService(
        config=pipeline.config,
        context=pipeline.context,
        logger=logger_port,
        metrics=pipeline.services.metrics,
    )

    # Create DataQualityService for DQ evaluation
    dq_service = DataQualityService(
        dq_monitor=pipeline.services.dq_monitor,
        config=pipeline.config.dq,
        logger=logger_port,
        metrics=pipeline.services.metrics,
        pipeline_name=pipeline.config.pipeline_name,
    )

    # Extract DQ configs from YAML config for DQ report generation
    dq_configs = _extract_dq_configs(yaml_config)

    postrun_service = PostrunService(
        config=pipeline.config,
        runtime=pipeline.runtime,
        dq_service=dq_service,
        lifecycle_service=lifecycle_service,
        metrics=pipeline.services.metrics,
        logger=logger_port,
        # DQ Report parameters
        dq_report_service=pipeline.services.dq_report_service,
        bronze_dq_config=dq_configs.bronze,
        silver_dq_config=dq_configs.silver,
        gold_dq_config=dq_configs.gold,
    )

    observer = PipelineObserver(
        pipeline_name=pipeline.config.pipeline_name,
        run_id=pipeline.context.run_id,
        run_type=pipeline.runtime.run_type,
        metrics=pipeline.services.metrics,
        logger=logger_port,
        tracer=observability.tracer,
    )

    # Extract sink paths for DQ report generation
    dq_output_paths = _extract_dq_output_paths(yaml_config)

    # Create unified BatchExecutor (replaces PipelineExecutor + RecordProcessor)
    # Safety Guard §4.6: lock validation via lock_validator callback
    batch_executor = ServicesBuilder.create_batch_executor_from_pipeline(
        pipeline=pipeline,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_manager.validate,
        tracer=observability.tracer,
        # DQ report output paths for flat_structure support
        bronze_output_path=dq_output_paths.bronze_path,
        silver_output_path=dq_output_paths.silver_path,
        gold_output_path=dq_output_paths.gold_path,
        flat_structure=dq_output_paths.flat_structure,
    )

    # Assemble Runner with directly injected services (explicit DI)
    return PipelineRunner(
        config=pipeline.config,
        runtime=pipeline.runtime,
        services=pipeline.services,
        context=pipeline.context,
        executor=batch_executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=pipeline.shutdown_signal,
        logger=logger_port,
        lock_manager=lock_manager,
        preflight=preflight_service,
        postrun=postrun_service,
        lifecycle_service=lifecycle_service,
        observer=observer,
        pipeline=pipeline,
        tracer=observability.tracer,
    )


def _extract_single_dq_config(
    sink: Any,
    layer_name: str,
    config_class: Any,
) -> Any | None:
    """Extract DQ config for a single layer.

    Args:
        sink: Sink configuration from YAML.
        layer_name: Name of the layer ('bronze', 'silver', 'gold').
        config_class: Pydantic config class for validation.

    Returns:
        DQ report config if enabled, None otherwise.

    Raises:
        ValidationError: If sink config exists but is invalid.
    """
    sink_config = sink.get(layer_name)
    if not sink_config:
        return None

    # Check if sink_config has model_dump (is a Pydantic model)
    if not hasattr(sink_config, "model_dump"):
        return None

    validated = config_class.model_validate(sink_config.model_dump())
    if hasattr(validated, "dq_report") and validated.dq_report.enabled:
        return validated.dq_report
    return None


def _extract_dq_configs(
    yaml_config: PipelineYamlConfig | None,
) -> DQConfigsContext:
    """Extract DQ report configs for each layer from YAML config.

    Args:
        yaml_config: Pipeline YAML configuration with sink settings.

    Returns:
        DQConfigsContext with bronze, silver, and gold DQ configurations.
        All values may be None if DQ reports are not configured.
    """
    from bioetl.infrastructure.schemas.dq_report_config import (
        BronzeSinkConfig,
        GoldSinkConfig,
        SilverSinkConfig,
    )

    if yaml_config is None:
        return DQConfigsContext(bronze=None, silver=None, gold=None)

    sink = getattr(yaml_config, "sink", None)
    if sink is None:
        return DQConfigsContext(bronze=None, silver=None, gold=None)

    bronze_config = _extract_single_dq_config(sink, "bronze", BronzeSinkConfig)
    silver_config = _extract_single_dq_config(sink, "silver", SilverSinkConfig)
    gold_config = _extract_single_dq_config(sink, "gold", GoldSinkConfig)

    return DQConfigsContext(
        bronze=bronze_config,
        silver=silver_config,
        gold=gold_config,
    )


def _get_layer_path(config: Any) -> str | None:
    """Extract path from layer config if available."""
    return getattr(config, "path", None) if config else None


def _has_flat_structure(config: Any) -> bool:
    """Check if layer config has flat_structure enabled."""
    return bool(config and getattr(config, "flat_structure", False))


def _extract_dq_output_paths(
    yaml_config: PipelineYamlConfig | None,
) -> DQOutputPathsContext:
    """Extract DQ report output paths and flat_structure from YAML config.

    Args:
        yaml_config: Pipeline YAML configuration with sink settings.

    Returns:
        DQOutputPathsContext with bronze_path, silver_path, gold_path, and flat_structure.
        Paths may be None if not configured.
    """
    if yaml_config is None:
        return DQOutputPathsContext(
            bronze_path=None, silver_path=None, gold_path=None, flat_structure=False
        )

    sink = getattr(yaml_config, "sink", None)
    if sink is None:
        return DQOutputPathsContext(
            bronze_path=None, silver_path=None, gold_path=None, flat_structure=False
        )

    bronze_config = sink.get("bronze")
    silver_config = sink.get("silver")
    gold_config = sink.get("gold")

    flat_structure = _has_flat_structure(silver_config) or _has_flat_structure(
        gold_config
    )

    return DQOutputPathsContext(
        bronze_path=_get_layer_path(bronze_config),
        silver_path=_get_layer_path(silver_config),
        gold_path=_get_layer_path(gold_config),
        flat_structure=flat_structure,
    )

================================================================================
File: runner_factory.py
Path: factories\runner_factory.py
================================================================================
"""Runner factory implementation for composition layer.

Implements RunnerFactoryPort and MetricsExtractorPort protocols
for the PipelineRunnerService.

This module provides the composition-layer implementation of runner
creation, allowing the application layer to remain independent of
bootstrap details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.providers.registration import register_all_providers
from bioetl.composition.registry import PipelineRegistry, get_default_registry

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import RunnablePort


class RunnerFactory:
    """Factory for creating pipeline runners.

    Implements RunnerFactoryPort protocol for PipelineRunnerService.
    Delegates to bootstrap_pipeline() for actual runner creation.

    Attributes:
        registry: Optional custom registry for test isolation.
    """

    def __init__(self, registry: PipelineRegistry | None = None) -> None:
        """Initialize the factory.

        Args:
            registry: Optional custom registry. If None, uses default.
        """
        self._registry = registry
        self._registrations_done = False

    def _ensure_registrations(self) -> None:
        """Ensure all providers and pipelines are registered.

        Idempotent - safe to call multiple times.
        """
        if not self._registrations_done:
            register_all_providers()
            register_all_pipelines(registry=self._registry)
            self._registrations_done = True

    @property
    def _effective_registry(self) -> PipelineRegistry:
        """Get the effective registry instance."""
        return self._registry if self._registry is not None else get_default_registry()

    def create(self, context: PipelineRunContext) -> RunnablePort:
        """Create a configured pipeline runner.

        Args:
            context: Pipeline run context containing all execution parameters.

        Returns:
            PipelineRunner ready for execution.

        Raises:
            ValueError: If pipeline name is unknown or config is invalid.
            FileNotFoundError: If pipeline config file is missing.
        """
        # Import inside method to avoid circular import:
        # composition/bootstrap.py -> _bootstrap/__init__.py -> _bootstrap/runner.py
        # -> factories/runner_factory.py -> composition/bootstrap.py
        from bioetl.composition.bootstrap import bootstrap_pipeline

        self._ensure_registrations()
        runner: PipelineRunner = bootstrap_pipeline(context, registry=self._registry)
        return runner

    def list_pipelines(self) -> list[str]:
        """List all available pipeline names.

        Returns:
            Sorted list of registered pipeline names.
        """
        self._ensure_registrations()
        return self._effective_registry.list_pipelines()

    def contains(self, pipeline_name: str) -> bool:
        """Check if a pipeline is registered.

        Args:
            pipeline_name: Name of the pipeline to check.

        Returns:
            True if pipeline exists, False otherwise.
        """
        self._ensure_registrations()
        return self._effective_registry.contains(pipeline_name)


class MetricsExtractor:
    """Extractor for pipeline execution metrics.

    Implements MetricsExtractorPort protocol for PipelineRunnerService.
    Extracts metrics from the runner's internal executor.
    """

    def extract_metrics(self, runner: RunnablePort) -> dict[str, int]:
        """Extract execution metrics from a runner.

        Args:
            runner: Runner to extract metrics from.

        Returns:
            Dictionary with metric names and values.
        """
        # Access the internal executor if available
        executor = getattr(runner, "_executor", None)

        if executor is None:
            return {
                "records_fetched": 0,
                "records_bronze": 0,
                "records_silver": 0,
                "records_gold": 0,
                "records_quarantined": 0,
            }

        return {
            "records_fetched": getattr(executor, "records_fetched", 0),
            "records_bronze": getattr(executor, "records_bronze", 0),
            "records_silver": getattr(executor, "records_silver", 0),
            "records_gold": getattr(executor, "records_gold", 0),
            "records_quarantined": getattr(executor, "records_quarantined", 0),
        }


def create_runner_factory(
    registry: PipelineRegistry | None = None,
) -> RunnerFactory:
    """Create a new RunnerFactory instance.

    Args:
        registry: Optional custom registry for test isolation.

    Returns:
        RunnerFactory instance.
    """
    return RunnerFactory(registry=registry)


def create_metrics_extractor() -> MetricsExtractor:
    """Create a new MetricsExtractor instance.

    Returns:
        MetricsExtractor instance.
    """
    return MetricsExtractor()

================================================================================
File: services_factory.py
Path: factories\services_factory.py
================================================================================
"""Services Factory.

Consolidated module for creating pipeline infrastructure services.

Contains:
- BaseServicesFactory: Creates PipelineServices with all dependencies
- ServicesBuilder: Creates CheckpointManager, RecordProcessor, BatchExecutor

This module follows the DI pattern: all services are created in the
composition layer and injected into pipeline components.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.dq_factory import DQServicesFactory
from bioetl.composition.factories.storage import StorageContext, StorageFactory
from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.medallion import LoadingStrategy
from bioetl.domain.ports import NoOpMetrics
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine import UnifiedQuarantine
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.config import MemoryConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        CheckpointPort,
        DataNormalizationPort,
        DataSourcePort,
        DQMonitorPort,
        LockPort,
        LoggerPort,
        MemoryMonitorPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )
    from bioetl.domain.services import DataNormalizationConfig
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


__all__ = [
    "BaseServicesFactory",
    "PipelineCallbacksContext",
    "ServicesBuilder",
    "create_data_normalization_service",
    "extract_pipeline_callbacks",
]


# =============================================================================
# Helper Functions
# =============================================================================


def extract_pipeline_callbacks(
    pipeline: BasePipeline,
) -> PipelineCallbacksContext:
    """Extract transformation callbacks from pipeline.

    Extracts callbacks from the pipeline's transformer if available,
    otherwise falls back to pipeline methods (legacy support).

    Args:
        pipeline: Pipeline instance with transformer or legacy methods.

    Returns:
        PipelineCallbacksContext with transform, gold_filter, and gold_transform callbacks.

    Raises:
        AttributeError: If pipeline has no transformer and doesn't implement
            transform_bronze_to_silver (enforces REQ-ARCH-REF-001).
    """
    transformer = pipeline.transformer
    if transformer is not None:
        return PipelineCallbacksContext(
            transform=transformer.transform,
            gold_filter=transformer.should_write_gold,
            gold_transform=transformer.transform_for_gold,
        )

    # Fallback for pipelines without explicit transformer (legacy)
    # NOTE: BasePipeline no longer implements these methods.
    # If a subclass does not implement them and has no transformer, this will raise AttributeError.
    # This is intentional to enforce the new architecture (REQ-ARCH-REF-001).
    transform_cb = pipeline.transform_bronze_to_silver
    gold_filter_cb = getattr(
        pipeline, "should_write_gold", lambda _context, record: True
    )
    gold_transform_cb = getattr(
        pipeline,
        "transform_for_gold",
        lambda _context, silver_record: silver_record,
    )
    return PipelineCallbacksContext(
        transform=transform_cb,
        gold_filter=gold_filter_cb,
        gold_transform=gold_transform_cb,
    )


# =============================================================================
# BaseServicesFactory - Creates PipelineServices
# =============================================================================


class BaseServicesFactory:
    """Reusable factory for common services (local deployment)."""

    @classmethod
    def create_common_services(
        cls,
        settings: Settings,
        logger: LoggerPort,
        data_source: DataSourcePort,
        pipeline_config: PipelineYamlConfig,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: Any = None,
    ) -> PipelineServices:
        """Create services with injected data source.

        Args:
            settings: Application settings
            logger: Structured logger
            data_source: Data source port implementation
            pipeline_config: Pipeline YAML configuration
            tracer: Optional tracer (defaults to NoOpTracing if not provided)
            dq_monitor: Optional data quality monitor for anomaly detection
            metadata_coordinator: Optional MetadataCoordinator for centralized
                                metadata creation across Bronze, Silver, Gold.
            silver_validator: Optional SilverValidatorPort for Pandera validation
                in SilverWriter. If None, SilverWriter uses NoOpSilverValidator.

        Returns:
            PipelineServices with all dependencies configured
        """
        # Create metrics first so it can be passed to storage factory
        metrics = cls._create_metrics(settings)

        storage_ctx = StorageFactory.create(
            settings,
            pipeline_config,
            logger,
            metrics=metrics,
            metadata_coordinator=metadata_coordinator,
            silver_validator=silver_validator,
        )

        lock = cls._create_lock()
        checkpoint = cls._create_checkpoint(storage_ctx)
        quarantine = cls._create_quarantine(settings)

        # Use provided tracer or fallback to NoOpTracing
        # Tracer should be created via bootstrap_tracer() for consistent configuration
        if tracer is None:
            from bioetl.domain.ports import NoOpTracing

            tracer = NoOpTracing()

        # Create DQ services if any layer has dq_report enabled
        dq_services = cls._create_dq_services(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
        )

        return PipelineServices(
            data_source=data_source,
            storage=storage_ctx.adapter,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            metrics=metrics,
            tracing=tracer,
            logger=logger,
            dq_monitor=dq_monitor,
            bronze_dq_analyzer=dq_services.get("bronze_analyzer"),
            silver_dq_analyzer=dq_services.get("silver_analyzer"),
            gold_dq_analyzer=dq_services.get("gold_analyzer"),
            dq_report_writer=dq_services.get("report_writer"),
            dq_report_service=dq_services.get("report_service"),
        )

    @staticmethod
    def _create_lock() -> LockPort:
        """Create in-memory lock for local deployment."""
        return MemoryLock()

    @staticmethod
    def _create_checkpoint(storage_ctx: StorageContext) -> CheckpointPort:
        """Create local filesystem checkpoint."""
        return LocalCheckpoint(base_path=storage_ctx.checkpoints_path)

    @staticmethod
    def _create_quarantine(settings: Settings) -> QuarantinePort:
        """Create unified quarantine storage independent of entity paths.

        Quarantine storage is centralized at data_dir/quarantine to avoid
        coupling with Silver path structure and simplify management.
        """
        return UnifiedQuarantine(
            base_path=str(settings.quarantine_path),
        )

    @staticmethod
    def _create_metrics(settings: Settings) -> MetricsPort:
        if settings.metrics_enabled:
            return PrometheusMetrics()
        return NoOpMetrics()

    @staticmethod
    def _get_output_root(
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> Path:
        """Derive output root from pipeline config or fall back to settings.

        DQ reports should be written alongside the data. This method extracts
        the output root from the bronze sink path configuration when available.

        For paths like 'data/output/bronze/chembl/activity':
        - parent = 'data/output/bronze/chembl'
        - parent.parent = 'data/output/bronze'
        - parent.parent.parent = 'data/output' (output root)

        Args:
            settings: Application settings.
            pipeline_config: Pipeline YAML configuration.

        Returns:
            Path to the output root directory.
        """
        bronze_config = pipeline_config.sink.get("bronze")

        # Use bronze path from config if available and not in test mode
        if not settings.test_mode and bronze_config and bronze_config.path:
            bronze_path = Path(bronze_config.path)
            # Go up 3 levels: bronze/provider/entity -> output root
            # e.g., data/output/bronze/chembl/activity -> data/output
            return bronze_path.parent.parent.parent

        # Fall back to settings data_dir
        return settings.data_dir

    @classmethod
    def _create_dq_services(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
    ) -> dict[str, Any]:
        """Create DQ services if any layer has dq_report enabled.

        Args:
            settings: Application settings.
            pipeline_config: Pipeline YAML configuration.
            logger: Structured logger.

        Returns:
            Dictionary with DQ services (empty if none enabled).
        """
        # Check if any DQ report is enabled in sink config
        dq_enabled = cls._is_dq_report_enabled(pipeline_config)

        if not dq_enabled:
            return {}

        # Create DQ analyzers
        bronze_analyzer = DQServicesFactory.create_bronze_analyzer()
        silver_analyzer = DQServicesFactory.create_silver_analyzer()
        gold_analyzer = DQServicesFactory.create_gold_analyzer()

        # DQ reports are written to dedicated reports/dq/ directory
        output_root = cls._get_output_root(settings, pipeline_config)
        dq_reports_path = output_root / "reports" / "dq"
        # Get flat_structure from sink config (use Silver as primary)
        flat_structure = cls._get_flat_structure(pipeline_config)
        report_writer = DQServicesFactory.create_report_writer(
            base_path=dq_reports_path,
            logger=logger,
            flat_structure=flat_structure,
        )

        # Create DQ report service
        from bioetl.application.services.dq_report_service import DQReportService

        report_service = DQReportService(
            logger=logger,
            bronze_analyzer=bronze_analyzer,
            silver_analyzer=silver_analyzer,
            gold_analyzer=gold_analyzer,
            report_writer=report_writer,
        )

        return {
            "bronze_analyzer": bronze_analyzer,
            "silver_analyzer": silver_analyzer,
            "gold_analyzer": gold_analyzer,
            "report_writer": report_writer,
            "report_service": report_service,
        }

    @staticmethod
    def _is_dq_report_enabled(config: PipelineYamlConfig) -> bool:
        """Check if any DQ report is enabled in pipeline config.

        Args:
            config: Pipeline YAML configuration.

        Returns:
            True if any layer has dq_report.enabled = true.
        """
        sink = config.sink

        # Check each layer for dq_report.enabled
        for layer_name in ("bronze", "silver", "gold"):
            layer_config = sink.get(layer_name)
            if layer_config and layer_config.dq_report.enabled:
                return True

        return False

    @staticmethod
    def _get_flat_structure(config: PipelineYamlConfig) -> bool:
        """Get flat_structure setting from pipeline config.

        Checks Silver and Gold layers for flat_structure setting.
        Returns True if either layer has flat_structure enabled.

        Args:
            config: Pipeline YAML configuration.

        Returns:
            True if flat_structure is enabled for any layer.
        """
        sink = config.sink

        # Check Silver and Gold for flat_structure
        for layer_name in ("silver", "gold"):
            layer_config = sink.get(layer_name)
            if layer_config and getattr(layer_config, "flat_structure", False):
                return True

        return False


# =============================================================================
# ServicesBuilder - Creates infrastructure components
# =============================================================================


class ServicesBuilder:
    """Builder for pipeline infrastructure components."""

    @staticmethod
    def create_checkpoint_manager(
        checkpoint_port: CheckpointPort,
        logger: LoggerPort,
        pipeline_name: str,
        run_id: RunID,
        resume: bool,
        *,
        loading_strategy: LoadingStrategy | None = None,
    ) -> CheckpointManager:
        """Create configured CheckpointManager.

        Args:
            checkpoint_port: Checkpoint storage port
            logger: Structured logger
            pipeline_name: Name of the pipeline
            run_id: Unique run identifier
            resume: Whether to resume from previous checkpoint
            loading_strategy: Loading strategy (ADR-031).
                FULL_SCAN_ONLY disables checkpoint resume.

        Returns:
            Configured CheckpointManager instance
        """
        return CheckpointManager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name=pipeline_name,
            run_id=run_id,
            resume=resume,
            loading_strategy=loading_strategy,
        )

    @staticmethod
    def create_record_processor(
        services: PipelineServices,
        context: PipelineContext,
        pipeline_name: str,
        provider: str,
        entity_type: str,
        silver_schema: pa.Schema | None,
        gold_schema: Any,
        dq_config: Any,
        primary_keys: Sequence[str],
        silver_table: str,
        gold_table: str | None,
        silver_write_mode: str,
        gold_write_mode: str,
        on_schema_mismatch: str,
        transform_callback: Any,
        gold_filter_callback: Any,
        gold_transform_callback: Any,
        *,
        strict_gold_validation: bool = False,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        column_groups: tuple[ColumnGroupConfig, ...] = (),
    ) -> RecordProcessor:
        """Create configured RecordProcessor.

        Args:
            services: Pipeline services
            context: Pipeline context
            pipeline_name: Name of the pipeline
            provider: Data provider name
            entity_type: Entity type being processed
            silver_schema: PyArrow schema for Silver layer
            gold_schema: Pandera schema for Gold layer
            dq_config: Data quality configuration
            primary_keys: Primary key fields
            silver_table: Silver table name
            gold_table: Gold table name
            silver_write_mode: Write mode for Silver
            gold_write_mode: Write mode for Gold
            on_schema_mismatch: Schema mismatch handling strategy
            transform_callback: Bronze to Silver transformation callback
            gold_filter_callback: Gold filtering callback
            gold_transform_callback: Silver to Gold transformation callback
            strict_gold_validation: If True, validation fails when gold_schema is None.
                Default False for backward compatibility.
            lock_validator: Async callable that validates lock ownership.
                Returns True if lock is still held, False otherwise.
                Typically LockManager.validate(). If None, lock validation
                is skipped (Safety Guard §4.6).

        Returns:
            Configured RecordProcessor instance
        """
        error_classifier = ErrorClassifier()
        table_config = TableConfig(
            primary_keys=tuple(primary_keys),
            silver_table=silver_table,
            gold_table=gold_table,
            silver_write_mode=silver_write_mode,
            gold_write_mode=gold_write_mode,
            on_schema_mismatch=on_schema_mismatch,  # type: ignore[arg-type]
        )

        processor_config = RecordProcessorConfig(
            pipeline_name=pipeline_name,
            provider=provider,
            entity_type=entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=dq_config,
            table_config=table_config,
            column_groups=column_groups,
        )

        # Create Gold validator from schema (DI pattern)
        # strict mode requires schema to be provided
        gold_validator = PanderaGoldValidator(
            gold_schema, strict=strict_gold_validation
        )

        return RecordProcessor(
            services=services,
            error_classifier=error_classifier,
            context=context,
            config=processor_config,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=gold_validator,
            lock_validator=lock_validator,
        )

    @staticmethod
    def create_record_processor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: Any,
        *,
        strict_gold_validation: bool = False,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ) -> RecordProcessor:
        """Create RecordProcessor from pipeline instance.

        Convenience method that extracts configuration from pipeline.

        Args:
            pipeline: Pipeline instance
            silver_schema: PyArrow schema for Silver layer
            gold_schema: Pandera schema for Gold layer
            strict_gold_validation: If True, validation fails when gold_schema is None.
                Default False for backward compatibility.
            lock_validator: Async callable that validates lock ownership.
                Returns True if lock is still held, False otherwise.
                Typically LockManager.validate(). If None, lock validation
                is skipped (Safety Guard §4.6).

        Returns:
            Configured RecordProcessor instance
        """
        callbacks = extract_pipeline_callbacks(pipeline)

        return ServicesBuilder.create_record_processor(
            services=pipeline.services,
            context=pipeline.context,
            pipeline_name=pipeline.config.pipeline_name,
            provider=pipeline.config.provider,
            entity_type=pipeline.config.entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=pipeline.config.dq,
            primary_keys=pipeline.config.primary_keys,
            silver_table=pipeline.config.silver_table,
            gold_table=pipeline.config.gold_table,
            silver_write_mode=pipeline.config.write_mode,
            gold_write_mode=pipeline.config.gold_write_mode,
            on_schema_mismatch=pipeline.config.on_schema_mismatch,
            transform_callback=callbacks.transform,
            gold_filter_callback=callbacks.gold_filter,
            gold_transform_callback=callbacks.gold_transform,
            strict_gold_validation=strict_gold_validation,
            lock_validator=lock_validator,
            column_groups=tuple(pipeline.config.column_groups),
        )

    @staticmethod
    def create_batch_executor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: Any,
        checkpoint_manager: CheckpointManager,
        shutdown_signal: ShutdownSignal,
        *,
        strict_gold_validation: bool = False,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        tracer: TracingPort | None = None,
        memory_monitor: MemoryMonitorPort | None = None,
        memory_config: MemoryConfig | None = None,
        # DQ report output paths (for flat_structure support)
        bronze_output_path: str | None = None,
        silver_output_path: str | None = None,
        gold_output_path: str | None = None,
        flat_structure: bool = False,
    ) -> BatchExecutor:
        """Create BatchExecutor from pipeline instance.

        This is the preferred method for creating batch executors as it
        consolidates PipelineExecutor and RecordProcessor into a single component.

        Args:
            pipeline: Pipeline instance.
            silver_schema: PyArrow schema for Silver layer.
            gold_schema: Pandera schema for Gold layer.
            checkpoint_manager: Checkpoint manager instance.
            shutdown_signal: Shutdown signal for graceful termination.
            strict_gold_validation: If True, validation fails when gold_schema is None.
            lock_validator: Async callable that validates lock ownership (Safety Guard §4.6).
            tracer: Optional tracing port for distributed tracing.
            memory_monitor: Optional memory monitor for adaptive batch sizing.
            memory_config: Memory configuration (used if memory_monitor not provided).

        Returns:
            Configured BatchExecutor instance.
        """
        callbacks = extract_pipeline_callbacks(pipeline)
        skip = pipeline.runtime.skip_gold
        gold_filter = (lambda _c, _r: False) if skip else callbacks.gold_filter

        # Build configuration
        error_classifier = ErrorClassifier()

        processor_config = RecordProcessorConfig(
            pipeline_name=pipeline.config.pipeline_name,
            provider=pipeline.config.provider,
            entity_type=pipeline.config.entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=pipeline.config.dq,
            table_config=pipeline.config.table,
            # DQ report output paths for flat_structure support
            bronze_output_path=bronze_output_path,
            silver_output_path=silver_output_path,
            gold_output_path=gold_output_path,
            flat_structure=flat_structure,
            column_groups=pipeline.config.column_groups,
        )

        # Create Gold validator
        gold_validator = PanderaGoldValidator(
            gold_schema, strict=strict_gold_validation
        )

        return BatchExecutor(
            services=pipeline.services,
            context=pipeline.context,
            config=processor_config,
            error_classifier=error_classifier,
            transform_callback=callbacks.transform,
            gold_filter_callback=gold_filter,
            gold_transform_callback=callbacks.gold_transform,
            gold_validator=gold_validator,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=shutdown_signal,
            batch_size=pipeline.config.batch_size,
            checkpoint_interval=pipeline.config.checkpoint_interval,
            tracer=tracer,
            lock_validator=lock_validator,
            memory_monitor=memory_monitor,
            memory_config=memory_config,
        )


# =============================================================================
# Domain Service Factory Functions
# =============================================================================


def create_data_normalization_service(
    config: DataNormalizationConfig | None = None,
) -> DataNormalizationPort:
    """Create DataNormalizationService with optional configuration.

    Factory function for creating DataNormalizationService instances.
    Uses default configuration if not provided.

    Args:
        config: Optional configuration for normalization behavior.

    Returns:
        DataNormalizationPort implementation (DefaultDataNormalizationService).

    Example:
        >>> from bioetl.composition.factories import create_data_normalization_service
        >>> normalizer = create_data_normalization_service()
        >>> normalizer.normalize_doi("10.1038/NATURE12373")
        '10.1038/nature12373'

        >>> from bioetl.domain.services import DataNormalizationConfig
        >>> config = DataNormalizationConfig(min_publication_year=1900)
        >>> normalizer = create_data_normalization_service(config)
    """
    from bioetl.domain.services import (
        DataNormalizationConfig,
        DefaultDataNormalizationService,
    )

    if config is None:
        config = DataNormalizationConfig()
    return DefaultDataNormalizationService(config=config)

================================================================================
File: storage.py
Path: factories\storage.py
================================================================================
"""Storage Module for Bronze/Silver/Gold layers.

Consolidated module for storage infrastructure - provides backward-compatible
re-exports from the split modules.

The actual implementations are now in:
- storage_adapter.py: StorageAdapter class (~330 LOC)
- storage_factory.py: StorageFactory and StorageContext (~120 LOC)

This module re-exports all public symbols for backward compatibility.
Existing imports like `from bioetl.composition.factories.storage import StorageFactory`
will continue to work.

Split per docs/REFACTORING_PLAN.md [P3] Storage Factory Split.
"""

from __future__ import annotations

# Re-export writers for test patching compatibility
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

# Re-export from split modules for backward compatibility
from .storage_adapter import StorageAdapter
from .storage_factory import StorageContext, StorageFactory

__all__ = [
    "BronzeWriter",
    "GoldWriter",
    "SilverWriter",
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
]

================================================================================
File: storage_adapter.py
Path: factories\storage_adapter.py
================================================================================
"""StorageAdapter - Unified storage adapter for Bronze/Silver/Gold layers.

Implements StoragePort protocol from domain/ports.py.

This module was extracted from storage.py as part of the storage factory split
to improve maintainability and reduce file size.

Note:
    Lock validation is performed at Application layer (BatchWriter)
    per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O adapters.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from bioetl.domain.types import HealthStatus
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.types import ArrowSchema, BatchID, RunID, RunType


__all__ = ["StorageAdapter"]


class StorageAdapter:
    """Unified storage adapter for Bronze/Silver/Gold.

    Implements StoragePort protocol from domain/ports.py.
    Delegates to specialized writers for each layer.
    """

    # Protocol compliance marker
    REQUIRES_SILVER_SCHEMA: bool = True

    def __init__(
        self,
        bronze_writer: BronzeWriter,
        silver_writer: SilverWriter,
        gold_writer: GoldWriter,
    ):
        self.bronze = bronze_writer
        self.silver = silver_writer
        self.gold = gold_writer

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeWriteResult:
        """Write raw records to Bronze layer.

        Args:
            records: Iterator of JSON-encoded record bytes.
            provider: Provider name.
            entity: Entity type.
            date: Date for path partitioning.
            batch_id: Unique batch identifier.
            run_id: Pipeline run identifier.
            run_type: Type of run.
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required.
            source_metadata: Optional pre-built SourceMetadata with API request
                           details for rich lineage tracking. If None, a minimal
                           SourceMetadata is created with type="api".

        Returns:
            BronzeWriteResult: Result containing path, record count, sizes,
                and checksum for downstream lineage tracking.

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        return await self.bronze.write_bronze(
            records=records,
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            source_metadata=source_metadata,
        )

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        column_order: list[str] | None = None,
        bronze_refs: list[BronzeWriteResult] | None = None,
    ) -> SilverWriteResult | None:
        """Write transformed records to Silver layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a transformed record.
            primary_keys: A list of column names that form the primary key.
            schema: The PyArrow schema definition for the records (ArrowSchema alias).
            mode: The write mode (e.g., 'merge', 'append', 'delete').
            partition_cols: Optional list of columns to partition by.
            on_schema_mismatch: How to handle schema drift.
            column_order: Optional explicit column order to apply.
            bronze_refs: Optional list of BronzeWriteResult from Bronze writes.
                If provided, bronze_paths will be populated in Silver metadata
                for complete lineage tracking (REQ-LINEAGE-001).

        Returns:
            SilverWriteResult with table info and Delta version for Gold lineage tracking
            (REQ-LINEAGE-002), or None if no records were written.

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        return await self.silver.write_silver(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            mode=mode,
            partition_cols=partition_cols,
            on_schema_mismatch=on_schema_mismatch,
            column_order=column_order,
            bronze_refs=bronze_refs,
        )

    async def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        schema: Any,
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
        *,
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: list[Any] | None = None,
    ) -> None:
        """Write aggregated records to Gold layer.

        Args:
            table_name: Target table name
            records: Records to write
            schema: Pandera schema for validation
            primary_keys: Optional primary key columns
            mode: Write mode
            column_order: Optional explicit column order to apply.
            ingestion_ts: Ingestion timestamp for audit (ADR-014)
            run_id: Run identifier for audit correlation
            silver_refs: Optional list of SilverWriteResult from Silver writes.
                If provided, source_tables will be populated in Gold metadata
                for complete lineage tracking (REQ-LINEAGE-002).

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        await self.gold.write_gold(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=primary_keys,
            mode=mode,
            column_order=column_order,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            silver_refs=silver_refs,
        )

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Read records from a Silver layer Delta table.

        Args:
            table_name: The name of the table to read (e.g., 'chembl/activity').
            columns: Optional list of columns to select. If None, reads all columns.

        Returns:
            List of dictionaries, where each dictionary represents a record.

        Raises:
            FileNotFoundError: If the table does not exist.
        """
        return await self.silver.read_silver(table_name, columns=columns)

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver layer without explicit schema.

        Used by composite pipelines where schema is dynamically determined.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical reordering.
        """
        await self.silver.write_silver_merged(
            table_name,
            records,
            primary_keys,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Gold layer without Pandera schema.

        Used by composite pipelines where schema is dynamically determined.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical reordering.
        """
        await self.gold.write_gold_merged(
            table_name,
            records,
            primary_keys,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Silver layer data for a specific table.

        Implements StoragePort.clear_silver().
        Clears both Delta tables and CSV exports (if configured).
        """
        return await self._run_clear(self.silver, table_name, dry_run)

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Gold layer data for a specific table.

        Implements StoragePort.clear_gold().
        Clears both Delta tables and CSV exports (if configured).
        """
        return await self._run_clear(self.gold, table_name, dry_run)

    async def _run_clear(
        self,
        writer: SilverWriter | GoldWriter,
        table_name: str,
        dry_run: bool,
    ) -> int:
        """Execute clear operation for a writer."""
        loop = asyncio.get_running_loop()
        cleared = await loop.run_in_executor(
            None, lambda: writer.clear(table_name, dry_run=dry_run)
        )
        if writer.csv_exporter and not dry_run:
            exporter = writer.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            cleared += len(deleted)
        return cleared

    async def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files for Silver and Gold layers.

        Implements StoragePort.clear_csv().
        """
        count = 0
        loop = asyncio.get_running_loop()

        if self.silver.csv_exporter:
            exporter = self.silver.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            count += len(deleted) if isinstance(deleted, list) else deleted

        if self.gold.csv_exporter:
            exporter = self.gold.csv_exporter
            deleted = await loop.run_in_executor(
                None, lambda: exporter.clear(table_name)
            )
            count += len(deleted) if isinstance(deleted, list) else deleted

        return count

    async def clear_delta(self, table_name: str | None = None) -> int:
        """Clear Delta tables for Silver and Gold layers.

        Implements StoragePort.clear_delta().

        Args:
            table_name: If provided, only clear Delta table for this table.
                       If None, clear all Delta tables.

        Returns:
            Number of tables cleared.
        """
        loop = asyncio.get_running_loop()
        cleared_count = 0

        if table_name:
            cleared_count += await loop.run_in_executor(
                None, lambda: self.silver.clear(table_name)
            )
            cleared_count += await loop.run_in_executor(
                None, lambda: self.gold.clear(table_name)
            )

        return cleared_count

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> dict[str, Any]:
        """Preview what would be cleared without actual deletion.

        Implements StoragePort.preview_cleanup().
        Used by CLI dry-run mode to show users what data would be affected.

        Args:
            silver_table: Silver table name (e.g., 'chembl.activity')
            gold_table: Optional Gold table name

        Returns:
            Dict with layer info including paths and file counts.
        """
        result: dict[str, Any] = {
            "silver": self._preview_layer(self.silver, silver_table),
            "gold": None,
            "total_files": 0,
        }

        if gold_table:
            result["gold"] = self._preview_layer(self.gold, gold_table)

        result["total_files"] = result["silver"]["file_count"] + (
            result["gold"]["file_count"] if result["gold"] else 0
        )
        return result

    def _preview_layer(
        self,
        writer: SilverWriter | GoldWriter,
        table_name: str,
    ) -> dict[str, Any]:
        """Count files in a layer without deletion.

        Args:
            writer: Delta or Gold writer instance
            table_name: Table name to preview

        Returns:
            Dict with path, file_count, and exists status.
        """
        path = writer.get_table_path(table_name)
        file_count = 0
        exists = path.exists()

        if exists:
            file_count = sum(1 for f in path.rglob("*") if f.is_file())

        return {
            "path": str(path),
            "file_count": file_count,
            "exists": exists,
        }

    async def aclose(self) -> None:
        """Close resources.

        Implements aclose() required by StoragePort protocol.
        """
        pass  # Writers don't need explicit cleanup

    async def health_check(self) -> HealthStatus:
        """Check storage accessibility and write capability.

        Validates Bronze, Silver, and Gold directories are writable by
        attempting to create and delete a temporary file in each layer.

        Returns:
            HealthStatus:
            - HEALTHY: All layers accessible and writable
            - DEGRADED: Partial access (1-2 layers have issues)
            - UNHEALTHY: Critical storage failure (all layers unavailable)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._check_storage_health_sync)

    def _check_storage_health_sync(self) -> HealthStatus:
        """Synchronous storage health check implementation.

        Checks if each layer's base directory is writable.
        """
        # Convert to Path objects since SilverWriter and GoldWriter store as strings
        layers = [
            ("bronze", Path(self.bronze.base_path)),
            ("silver", Path(self.silver.base_path)),
            ("gold", Path(self.gold.base_path)),
        ]

        issues = 0
        for _layer_name, base_path in layers:
            if not self._check_directory_writable(base_path):
                issues += 1

        if issues == 0:
            return HealthStatus.HEALTHY
        elif issues < len(layers):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    async def optimize(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> None:
        """Optimize storage for a specific table/entity.

        Performs maintenance operations appropriate for the storage layer:
        - Delta Lake: Runs VACUUM to remove old files
        - JSONL/File: Removes files older than retention period

        Args:
            table_name: Target identifier (e.g., 'provider.entity' for Delta/Bronze)
            retention_hours: Retention period in hours (default 168h = 7 days)
            dry_run: If True, only log what would be done without action
        """
        # 1. Optimize Silver/Gold Delta Tables
        await self.vacuum(table_name, retention_hours, dry_run)

        # 2. Optimize Bronze (File cleanup)
        # Parse table_name to get provider/entity for targeted cleanup
        if "." in table_name:
            provider, entity = table_name.split(".", 1)
            cutoff_date = datetime.now(UTC) - timedelta(hours=retention_hours)
            await self.bronze.cleanup_old_files(
                cutoff_date=cutoff_date,
                dry_run=dry_run,
                provider=provider,
                entity=entity,
            )

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table via underlying writers.

        Implements StoragePort.vacuum().
        Vacuums both Silver and Gold layers for the specified table.

        Args:
            table_name: Table name in format "provider.entity"
            retention_hours: Minimum age of files to remove (default 168h = 7 days)
            dry_run: If True, only report what would be removed

        Returns:
            Total number of files removed (or would be removed if dry_run)
        """
        total_removed = 0

        # Vacuum Silver (only if table exists)
        silver_table_path = self.silver.get_table_path(table_name)
        if silver_table_path.exists():
            removed = await self.silver.vacuum(
                table_name=table_name,
                retention_hours=retention_hours,
                dry_run=dry_run,
            )
            total_removed += len(removed)

        # Vacuum Gold (only if table exists)
        gold_table_path = self.gold.get_table_path(table_name)
        if gold_table_path.exists():
            from deltalake import DeltaTable

            loop = asyncio.get_running_loop()
            dt = await loop.run_in_executor(
                None,
                lambda: DeltaTable(str(gold_table_path)),
            )
            removed = await loop.run_in_executor(
                None,
                lambda: dt.vacuum(retention_hours=retention_hours, dry_run=dry_run),
            )
            total_removed += len(removed)

        return total_removed

    async def archive(
        self,
        table_name: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive table to target path.

        Implements StoragePort.archive().
        Archives both Silver and Gold layers for the specified table.

        Args:
            table_name: Table name to archive
            target_path: Destination path for archive
            remove_source: If True, remove source after successful copy

        Returns:
            Number of files archived
        """
        import shutil

        total_archived = 0

        # Archive Silver
        silver_table_path = self.silver.get_table_path(table_name)
        if silver_table_path.exists():
            silver_target = Path(target_path) / "silver" / table_name.replace(".", "/")
            silver_target.parent.mkdir(parents=True, exist_ok=True)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: shutil.copytree(silver_table_path, silver_target),
            )
            total_archived += sum(
                1 for f in silver_table_path.rglob("*") if f.is_file()
            )
            if remove_source:
                await loop.run_in_executor(
                    None,
                    lambda: shutil.rmtree(silver_table_path),
                )

        # Archive Gold
        gold_table_path = self.gold.get_table_path(table_name)
        if gold_table_path.exists():
            gold_target = Path(target_path) / "gold" / table_name.replace(".", "/")
            gold_target.parent.mkdir(parents=True, exist_ok=True)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: shutil.copytree(gold_table_path, gold_target),
            )
            total_archived += sum(1 for f in gold_table_path.rglob("*") if f.is_file())
            if remove_source:
                await loop.run_in_executor(
                    None,
                    lambda: shutil.rmtree(gold_table_path),
                )

        return total_archived

    async def cleanup_bronze(
        self,
        cutoff_date: datetime,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Remove Bronze files older than cutoff date (RULES.md §2.1 retention).

        Implements StoragePort.cleanup_bronze().
        Delegates to BronzeWriter.cleanup_old_files().

        Args:
            cutoff_date: Files older than this date will be removed.
            dry_run: If True, only count what would be removed.

        Returns:
            Dictionary with cleanup statistics.
        """
        return await self.bronze.cleanup_old_files(
            cutoff_date=cutoff_date,
            dry_run=dry_run,
        )

    @staticmethod
    def _check_directory_writable(dir_path: Path | str) -> bool:
        """Check if a directory is writable.

        Args:
            dir_path: Directory path to check (accepts Path or str).

        Returns:
            True if directory is writable, False otherwise.
        """
        try:
            # Convert to Path if string
            path = Path(dir_path) if isinstance(dir_path, str) else dir_path

            # Ensure directory exists
            path.mkdir(parents=True, exist_ok=True)

            # Try to create and delete a temporary file
            temp_file = path / ".health_check_probe"
            temp_file.touch()
            temp_file.unlink()
            return True
        except (OSError, PermissionError):
            return False

================================================================================
File: storage_factory.py
Path: factories\storage_factory.py
================================================================================
"""StorageFactory - Factory for creating StorageAdapters.

Creates configured StorageAdapters for local deployment with proper
Bronze, Silver, and Gold writers.

This module was extracted from storage.py as part of the storage factory split
to improve maintainability and reduce file size.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import NoOpMetadataWriter, NoOpTracing
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

from .storage_adapter import StorageAdapter

if TYPE_CHECKING:
    from typing import Any

    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


__all__ = ["StorageContext", "StorageFactory"]


@dataclass(frozen=True)
class StorageContext:
    """Context object returned by StorageFactory containing adapter and paths."""

    adapter: StorageAdapter
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    checkpoints_path: Path


class StorageFactory:
    """Factory for creating configured StorageAdapters for local deployment."""

    @staticmethod
    def _create_metadata_writer(
        enabled: bool, logger: LoggerPort
    ) -> MetadataWriter | NoOpMetadataWriter:
        """Create a MetadataWriter or NoOp based on configuration."""
        if enabled:
            return MetadataWriter(logger=logger)
        return NoOpMetadataWriter()

    @staticmethod
    def _create_csv_exporter_from_config(
        csv_cfg: Any,
        logger: LoggerPort,
        override_path: Path | None = None,
    ) -> CsvExporter | None:
        """Create a CsvExporter from configuration if enabled.

        Args:
            csv_cfg: CSV export configuration from YAML.
            logger: Logger for observability.
            override_path: If provided, use this path instead of csv_cfg.path.
                          Used in test mode to respect test isolation.
        """
        if csv_cfg and csv_cfg.enabled:
            # Convert to str for CsvExporter (expects str, not Path)
            path = override_path or csv_cfg.path
            return CsvExporter(
                base_path=str(path),
                logger=logger,
                delimiter=csv_cfg.delimiter,
                header=csv_cfg.header,
                encoding=csv_cfg.encoding,
            )
        return None

    @staticmethod
    def _resolve_layer_path(
        layer_config: Any, default_path: Path, use_yaml_paths: bool
    ) -> Path:
        """Resolve storage path from config or fall back to default."""
        if use_yaml_paths and layer_config and layer_config.path:
            return Path(layer_config.path)
        return default_path

    @staticmethod
    def _create_storage_adapter(
        bronze_path: Path,
        silver_path: Path,
        gold_path: Path,
        bronze_config: Any,
        silver_config: Any,
        gold_config: Any,
        silver_csv_exporter: CsvExporter | None,
        gold_csv_exporter: CsvExporter | None,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort | None,
        metadata_coordinator: MetadataCoordinator | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        bronze_flat_structure: bool = False,
        silver_flat_structure: bool = False,
        gold_flat_structure: bool = False,
        silver_validator: Any = None,
    ) -> StorageAdapter:
        """Create StorageAdapter with all writers configured.

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.
        """
        save_json = bronze_config.save_json if bronze_config else False
        bronze_save_metadata = bronze_config.save_metadata if bronze_config else False
        # JSON files are now written alongside zst files (same directory)
        # No separate json_path needed

        # Ensure tracing is always explicitly provided (DI pattern)
        effective_tracing: TracingPort = tracing or NoOpTracing()

        # Create metadata writers using Null Object pattern
        silver_save_metadata = silver_config.save_metadata if silver_config else False
        gold_save_metadata = gold_config.save_metadata if gold_config else False

        bronze_metadata_writer = StorageFactory._create_metadata_writer(
            bronze_save_metadata, logger
        )
        silver_metadata_writer = StorageFactory._create_metadata_writer(
            silver_save_metadata, logger
        )
        gold_metadata_writer = StorageFactory._create_metadata_writer(
            gold_save_metadata, logger
        )

        return StorageAdapter(
            bronze_writer=BronzeWriter(
                base_path=bronze_path,
                logger=logger,
                metrics=metrics,
                tracing=effective_tracing,
                save_json=save_json,
                json_path=None,  # JSON is now written alongside zst files
                metadata_writer=bronze_metadata_writer,
                save_metadata=bronze_save_metadata,
                metadata_coordinator=metadata_coordinator,
                flat_structure=bronze_flat_structure,
            ),
            silver_writer=SilverWriter(
                base_path=silver_path,
                logger=logger,
                tracing=effective_tracing,
                csv_exporter=silver_csv_exporter,
                silver_validator=silver_validator,
                metadata_writer=silver_metadata_writer,
                metadata_coordinator=metadata_coordinator,
                transform_version=transform_version,
                transform_steps=transform_steps,
                flat_structure=silver_flat_structure,
            ),
            gold_writer=GoldWriter(
                base_path=gold_path,
                logger=logger,
                tracing=effective_tracing,
                csv_exporter=gold_csv_exporter,
                metadata_writer=gold_metadata_writer,
                metadata_coordinator=metadata_coordinator,
                transform_version=transform_version,
                transform_steps=transform_steps,
                flat_structure=gold_flat_structure,
            ),
        )

    @staticmethod
    def create(
        settings: Settings,
        config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: Any = None,
    ) -> StorageContext:
        """Create a StorageAdapter for local deployment.

        Args:
            settings: Application settings with data_dir
            config: Pipeline YAML configuration
            logger: Structured logger
            metrics: Metrics port for Bronze observability (MUST be injected).
            tracing: Optional TracingPort for distributed tracing.
            metadata_coordinator: Optional MetadataCoordinator for centralized
                                metadata creation. If provided, ensures consistent
                                run_id and timestamps across Bronze, Silver, Gold.
            silver_validator: Optional SilverValidatorPort for Pandera validation
                in SilverWriter. If None, SilverWriter uses NoOpSilverValidator.

        Returns:
            StorageContext with adapter and paths
        """
        bronze_config = config.sink.get("bronze")
        silver_config = config.sink.get("silver")
        gold_config = config.sink.get("gold")

        # In test mode, always use settings to respect test isolation
        use_yaml_paths = not settings.test_mode

        bronze_path = StorageFactory._resolve_layer_path(
            bronze_config, settings.bronze_path, use_yaml_paths
        )
        silver_path = StorageFactory._resolve_layer_path(
            silver_config, settings.silver_path, use_yaml_paths
        )
        gold_path = StorageFactory._resolve_layer_path(
            gold_config, settings.gold_path, use_yaml_paths
        )

        logger.info(
            "Using local storage",
            bronze_path=str(bronze_path),
            silver_path=str(silver_path),
            gold_path=str(gold_path),
        )

        # In test mode, override CSV export paths to use resolved layer paths
        # This ensures test isolation by writing to temp directories
        silver_csv_exporter = StorageFactory._create_csv_exporter_from_config(
            silver_config.csv_export if silver_config else None,
            logger,
            override_path=silver_path if settings.test_mode else None,
        )
        gold_csv_exporter = StorageFactory._create_csv_exporter_from_config(
            gold_config.csv_export if gold_config else None,
            logger,
            override_path=gold_path if settings.test_mode else None,
        )

        # JSON files are now written alongside zst files (same directory)
        save_json = bronze_config.save_json if bronze_config else False

        bronze_save_metadata = bronze_config.save_metadata if bronze_config else False
        silver_save_metadata = silver_config.save_metadata if silver_config else False
        gold_save_metadata = gold_config.save_metadata if gold_config else False
        StorageFactory._log_export_status(
            logger,
            save_json,
            silver_csv_exporter,
            gold_csv_exporter,
            bronze_save_metadata,
            silver_save_metadata,
            gold_save_metadata,
        )

        # Extract transform info for lineage tracking
        transform_version = config.transform.version
        transform_steps = tuple(config.transform.steps)

        # Extract flat_structure settings
        # In test mode (use_yaml_paths=False), settings paths don't include
        # provider/entity segments, so flat_structure must be False to ensure
        # each pipeline writes to its own subdirectory (base_path/table_name).
        # In production, YAML paths already include provider/entity per ADR-029,
        # so flat_structure=true correctly writes directly to the configured path.
        bronze_flat_structure = (
            bronze_config.flat_structure if bronze_config else False
        ) and use_yaml_paths
        silver_flat_structure = (
            silver_config.flat_structure if silver_config else False
        ) and use_yaml_paths
        gold_flat_structure = (
            gold_config.flat_structure if gold_config else False
        ) and use_yaml_paths

        adapter = StorageFactory._create_storage_adapter(
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            bronze_config=bronze_config,
            silver_config=silver_config,
            gold_config=gold_config,
            silver_csv_exporter=silver_csv_exporter,
            gold_csv_exporter=gold_csv_exporter,
            logger=logger,
            metrics=metrics,
            tracing=tracing,
            metadata_coordinator=metadata_coordinator,
            transform_version=transform_version,
            transform_steps=transform_steps,
            bronze_flat_structure=bronze_flat_structure,
            silver_flat_structure=silver_flat_structure,
            gold_flat_structure=gold_flat_structure,
            silver_validator=silver_validator,
        )

        return StorageContext(
            adapter=adapter,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            checkpoints_path=settings.checkpoint_path,
        )

    @staticmethod
    def _log_export_status(
        logger: LoggerPort,
        save_json: bool,
        silver_csv_exporter: CsvExporter | None,
        gold_csv_exporter: CsvExporter | None,
        bronze_save_metadata: bool = False,
        silver_save_metadata: bool = False,
        gold_save_metadata: bool = False,
    ) -> None:
        """Log export configuration status."""
        if save_json:
            logger.info("JSON export enabled for Bronze layer (alongside zst files)")
        if bronze_save_metadata:
            logger.info("metadata_export_enabled", layer="bronze")
        if silver_save_metadata:
            logger.info("metadata_export_enabled", layer="silver")
        if gold_save_metadata:
            logger.info("metadata_export_enabled", layer="gold")
        if silver_csv_exporter:
            logger.info(
                "csv_export_enabled",
                layer="silver",
                base_path=str(silver_csv_exporter.base_path),
            )
        if gold_csv_exporter:
            logger.info(
                "csv_export_enabled",
                layer="gold",
                base_path=str(gold_csv_exporter.base_path),
            )

================================================================================
File: transformer_factory.py
Path: factories\transformer_factory.py
================================================================================
# src/bioetl/composition/factories/transformer_factory.py
"""Transformer Factory for DI-based transformer creation.

This module provides factory functions for creating transformers,
enabling Dependency Injection instead of creating transformers inside pipelines.

Usage:
    >>> from bioetl.composition.factories.transformer_factory import create_transformer
    >>> transformer = create_transformer("chembl", "activity")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.services import IdentityService

# Mapping of (provider, entity_type) to transformer class
_TRANSFORMER_REGISTRY: dict[tuple[str, str], type[BaseTransformer]] = {}


def register_transformer(
    provider: str,
    entity_type: str,
    transformer_class: type[BaseTransformer],
) -> None:
    """Register a transformer class for a provider/entity combination.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').
        entity_type: Entity type (e.g., 'activity', 'compound').
        transformer_class: The transformer class to register.

    """
    _TRANSFORMER_REGISTRY[(provider, entity_type)] = transformer_class


def create_transformer(
    provider: str,
    entity_type: str,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    silver_filters: SilverFilterConfig | GoldFilterConfig | None = None,
    gold_filters: GoldFilterConfig | None = None,
    identity_service: IdentityService | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
) -> BaseTransformer:
    """Create a transformer instance for the given provider and entity type.

    This is the main factory function for creating transformers via DI.
    Uses the transformer registry to find the appropriate class.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').
        entity_type: Entity type (e.g., 'activity', 'compound').
        tracer: Optional tracing port for distributed tracing (O1 observability).
        metrics: Optional metrics port for duration/error tracking (O1 observability).
        silver_filters: Optional domain-level filter configuration for Silver layer.
        gold_filters: Optional filter configuration for Gold layer.
        identity_service: Service for computing entity IDs and content hashes.
            Defaults to a new IdentityService instance in BaseTransformer.
        pii_hasher: Optional PII hasher for hashing author names and other PII.
            Defaults to NoOpPiiHasher (no hashing) in BaseTransformer.
        data_normalizer: Optional data normalization service for text normalization
            (DOI, PMID, authors, HTML). Defaults to DataNormalizationService.

    Returns:
        Configured transformer instance with observability.

    Raises:
        KeyError: If no transformer is registered for the provider/entity combination.

    Example:
        >>> transformer = create_transformer("chembl", "activity")
        >>> isinstance(transformer, ActivityTransformer)
        True

    """
    key = (provider, entity_type)
    if key not in _TRANSFORMER_REGISTRY:
        raise KeyError(
            f"No transformer registered for provider='{provider}', "
            f"entity_type='{entity_type}'. "
            f"Available: {list(_TRANSFORMER_REGISTRY.keys())}"
        )

    transformer_class = _TRANSFORMER_REGISTRY[key]
    return transformer_class(
        provider=provider,
        entity_type=entity_type,
        tracer=tracer,
        metrics=metrics,
        silver_filters=silver_filters,
        gold_filters=gold_filters,
        identity_service=identity_service,
        pii_hasher=pii_hasher,
        data_normalizer=data_normalizer,
    )


def get_transformer_class(
    provider: str,
    entity_type: str,
) -> type[BaseTransformer] | None:
    """Get transformer class without instantiating.

    Args:
        provider: Provider name.
        entity_type: Entity type.

    Returns:
        Transformer class if registered, None otherwise.

    """
    return _TRANSFORMER_REGISTRY.get((provider, entity_type))


def register_all_transformers() -> None:
    """Register all known transformers.

    Called during application startup to populate the registry.
    Idempotent - safe to call multiple times.
    """
    # Import here to avoid circular imports
    from bioetl.application.pipelines.chembl.activity_transformer import (
        ActivityTransformer,
    )
    from bioetl.application.pipelines.chembl.assay_parameters_transformer import (
        AssayParametersTransformer,
    )
    from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
    from bioetl.application.pipelines.chembl.cell_line_transformer import (
        CellLineTransformer,
    )
    from bioetl.application.pipelines.chembl.compound_record_transformer import (
        CompoundRecordTransformer,
    )
    from bioetl.application.pipelines.chembl.molecule_transformer import (
        MoleculeTransformer,
    )
    from bioetl.application.pipelines.chembl.protein_class_transformer import (
        ProteinClassTransformer,
    )
    from bioetl.application.pipelines.chembl.publication_similarity_transformer import (
        PublicationSimilarityTransformer,
    )
    from bioetl.application.pipelines.chembl.publication_term_transformer import (
        PublicationTermTransformer,
    )
    from bioetl.application.pipelines.chembl.publication_transformer import (
        PublicationTransformer,
    )
    from bioetl.application.pipelines.chembl.subcellular_fraction_transformer import (
        SubcellularFractionTransformer,
    )
    from bioetl.application.pipelines.chembl.target_component_transformer import (
        TargetComponentTransformer,
    )
    from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
    from bioetl.application.pipelines.crossref.transformer import (
        CrossRefPublicationTransformer,
    )
    from bioetl.application.pipelines.openalex.transformer import (
        OpenAlexPublicationTransformer,
    )
    from bioetl.application.pipelines.pubchem.transformer import (
        PubChemCompoundTransformer,
    )
    from bioetl.application.pipelines.pubmed.transformer import (
        PubMedPublicationTransformer,
    )
    from bioetl.application.pipelines.semanticscholar.transformer import (
        SemanticScholarPublicationTransformer,
    )
    from bioetl.application.pipelines.uniprot.idmapping_transformer import (
        IDMappingTransformer,
    )
    from bioetl.application.pipelines.uniprot.transformer import (
        UniProtProteinTransformer,
    )

    # ChEMBL transformers
    register_transformer("chembl", "activity", ActivityTransformer)
    register_transformer("chembl", "assay", AssayTransformer)
    register_transformer("chembl", "assay_parameters", AssayParametersTransformer)
    register_transformer("chembl", "cell_line", CellLineTransformer)
    register_transformer("chembl", "compound_record", CompoundRecordTransformer)
    register_transformer("chembl", "document", PublicationTransformer)
    register_transformer(
        "chembl", "document_similarity", PublicationSimilarityTransformer
    )
    register_transformer("chembl", "document_term", PublicationTermTransformer)
    register_transformer("chembl", "molecule", MoleculeTransformer)
    register_transformer(
        "chembl", "subcellular_fraction", SubcellularFractionTransformer
    )
    register_transformer("chembl", "protein_class", ProteinClassTransformer)
    register_transformer("chembl", "target", TargetTransformer)
    register_transformer("chembl", "target_component", TargetComponentTransformer)

    # PubChem transformers
    register_transformer("pubchem", "compound", PubChemCompoundTransformer)

    # UniProt transformers
    register_transformer("uniprot", "protein", UniProtProteinTransformer)
    register_transformer("uniprot", "idmapping", IDMappingTransformer)

    # PubMed transformers
    register_transformer("pubmed", "publication", PubMedPublicationTransformer)

    # CrossRef transformers
    register_transformer("crossref", "publication", CrossRefPublicationTransformer)

    # OpenAlex transformers
    register_transformer("openalex", "publication", OpenAlexPublicationTransformer)

    # Semantic Scholar transformers
    register_transformer(
        "semanticscholar", "publication", SemanticScholarPublicationTransformer
    )


__all__ = [
    "create_transformer",
    "get_transformer_class",
    "register_all_transformers",
    "register_transformer",
]

================================================================================
File: observability.py
Path: observability.py
================================================================================
"""Observability bundle for unified dependency injection.

Aggregates logger, tracer, and metrics into a single injectable dependency,
simplifying constructor signatures across the codebase.

This module enforces the Unified Observability Contract:
- logger: REQUIRED - pipeline cannot run without structured logging
- metrics: REQUIRED - always valid implementation (NoOpMetrics fallback)
- tracer: Optional - distributed tracing
- dq_monitor: Optional - data quality anomaly detection
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort

if TYPE_CHECKING:
    from bioetl.domain.ports import DQMonitorPort


class ObservabilityContractError(Exception):
    """Raised when observability contract requirements are not met.

    This error indicates a programming error in the bootstrap/composition layer
    where required observability components were not properly initialized.
    """


@dataclass(frozen=True)
class ObservabilityBundle:
    """Unified observability context for pipeline execution.

    Aggregates logger, tracer, metrics, and data quality monitor into
    a single injectable dependency. This reduces the number of constructor
    parameters and ensures consistent observability configuration across components.

    Unified Observability Contract:
    - logger: REQUIRED - structured logger, cannot be None
    - metrics: REQUIRED - MetricsPort implementation (NoOpMetrics if disabled)
    - tracer: Optional - distributed tracing port
    - dq_monitor: Optional - data quality anomaly detector

    Raises:
        ObservabilityContractError: If required components are None.

    Attributes:
        logger: Structured logger for the pipeline.
        metrics: Metrics collection port (never None - uses NoOpMetrics fallback).
        tracer: Optional distributed tracing port.
        dq_monitor: Optional data quality anomaly detector.
    """

    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None

    def __post_init__(self) -> None:
        """Validate that required observability components are present."""
        if self.logger is None:
            raise ObservabilityContractError(
                "Logger is required. Cannot run pipeline without structured logging. "
                "Use bootstrap_observability() to create a valid bundle."
            )
        if self.metrics is None:
            raise ObservabilityContractError(
                "Metrics port is required. Use NoOpMetrics when metrics are disabled. "
                "Use bootstrap_observability() to create a valid bundle."
            )

    @classmethod
    def create(
        cls,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
    ) -> ObservabilityBundle:
        """Factory method for creating observability bundle.

        Enforces the Unified Observability Contract by requiring
        valid logger and metrics implementations.

        Args:
            logger: Structured logger instance (required).
            metrics: Metrics port implementation (required, use NoOpMetrics if disabled).
            tracer: Optional tracer port.
            dq_monitor: Optional data quality monitor port.

        Returns:
            Configured ObservabilityBundle instance.

        Raises:
            ObservabilityContractError: If logger or metrics is None.
        """
        return cls(logger=logger, metrics=metrics, tracer=tracer, dq_monitor=dq_monitor)

    def bind(self, **kwargs: object) -> ObservabilityBundle:
        """Create new bundle with bound logger context.

        Creates a new bundle with additional context bound to the logger.
        Useful for adding request-specific context (e.g., run_id, entity_id).

        Args:
            **kwargs: Key-value pairs to bind to the logger.

        Returns:
            New ObservabilityBundle with bound logger context.
        """
        return ObservabilityBundle(
            logger=self.logger.bind(**kwargs),
            tracer=self.tracer,
            metrics=self.metrics,
            dq_monitor=self.dq_monitor,
        )


__all__ = ["ObservabilityBundle", "ObservabilityContractError"]

================================================================================
File: __init__.py
Path: providers\__init__.py
================================================================================
"""Provider registration system.

Provides unified API for registering data source providers.

Example:
    >>> from bioetl.composition.providers import (
    ...     ProviderRegistry,
    ...     load_providers,
    ...     register_all_providers,
    ... )
    >>>
    >>> # Load all providers
    >>> load_providers()
    >>>
    >>> # Get provider configuration
    >>> config = ProviderRegistry.get("chembl")
    >>> config.http_config.rate
    10.0
"""

from bioetl.composition.providers.decorators import register_provider
from bioetl.composition.providers.loader import (
    ensure_providers_loaded,
    load_providers,
)
from bioetl.composition.providers.provider_registry import (
    DataSourceCreator,
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)
from bioetl.composition.providers.registration import register_all_providers

__all__ = [
    "DataSourceCreator",
    "HttpConfig",
    "ProviderConfig",
    "ProviderRegistry",
    "ensure_providers_loaded",
    "load_providers",
    "register_all_providers",
    "register_provider",
]

================================================================================
File: _config_helpers.py
Path: providers\_config_helpers.py
================================================================================
"""Configuration helpers for provider registration.

Utility functions for loading and extracting provider configuration
from YAML source configs. Split from registration.py per
audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.filtered_data_source import FilteredDataSource
from bioetl.composition.bootstrap_contexts import (
    CircuitBreakerConfig,
    RateLimitConfig,
)
from bioetl.domain.resilience import AdapterConfig
from bioetl.infrastructure.adapters.input.csv_filter_reader import CsvFilterReader
from bioetl.infrastructure.config import load_source_config

if TYPE_CHECKING:
    from typing import Any

    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def _get_factories() -> tuple[Any, Any]:
    """Lazy import factories to avoid circular imports."""
    from bioetl.composition.factories.data_source_factory import DataSourceFactory
    from bioetl.composition.factories.http_client_factory import HttpClientFactory

    return DataSourceFactory, HttpClientFactory


def _get_source_config(provider: str) -> SourceYamlConfig | None:
    """Load config from configs/sources/{provider}.yaml or return None.

    Returns:
        SourceYamlConfig if found, None if config file does not exist.

    Raises:
        ValueError: If config file exists but is invalid.
    """
    from pathlib import Path

    config_path = Path(f"configs/sources/{provider}.yaml")
    if not config_path.exists():
        return None
    return load_source_config(provider)


def _get_batch_size_from_config(provider: str, default: int = 100) -> int:
    """Get batch size from source config or return default."""
    source_config = _get_source_config(provider)
    return source_config.batch_size if source_config else default


def _get_rate_limit_from_config(provider: str) -> RateLimitConfig:
    """Get rate limit configuration from source config or defaults.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').

    Returns:
        RateLimitConfig with rate and capacity values.
    """
    source_config = _get_source_config(provider)
    if source_config:
        return RateLimitConfig(
            rate=source_config.rate_limit.requests_per_second,
            capacity=source_config.rate_limit.burst,
        )
    return RateLimitConfig(rate=5.0, capacity=10)


def _get_circuit_breaker_from_config(provider: str) -> CircuitBreakerConfig:
    """Get circuit breaker configuration from source config or defaults.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').

    Returns:
        CircuitBreakerConfig with failure_threshold and recovery_timeout.
    """
    source_config = _get_source_config(provider)
    if source_config:
        return CircuitBreakerConfig(
            failure_threshold=source_config.circuit_breaker.failure_threshold,
            recovery_timeout=source_config.circuit_breaker.recovery_timeout,
        )
    return CircuitBreakerConfig(failure_threshold=5, recovery_timeout=300)


def _get_adapter_config(provider: str, default_page_size: int = 1000) -> AdapterConfig:
    """Get AdapterConfig from source YAML config.

    This is the single source of truth for adapter parameters (RULES.md §12.1.2).
    Loads from configs/sources/{provider}.yaml and converts to domain dataclass.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem')
        default_page_size: Default page size if not specified in config

    Returns:
        AdapterConfig: Immutable adapter configuration

    Raises:
        ValueError: If source config file exists but is invalid.
    """
    source_config = _get_source_config(provider)
    if source_config is not None:
        return source_config.to_adapter_config(default_page_size=default_page_size)

    # Fallback to domain defaults when config file does not exist
    return AdapterConfig(page_size=default_page_size)


def _wrap_with_filter(
    data_source: DataSourcePort,
    filter_config: InputFilterConfig | None,
    logger: LoggerPort | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Wrap data source with FilteredDataSource if filter is enabled."""
    if filter_config and filter_config.enabled:
        return FilteredDataSource(
            data_source=data_source,
            filter_reader=CsvFilterReader(logger=logger),
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
            logger=logger,
        )
    return data_source

================================================================================
File: decorators.py
Path: providers\decorators.py
================================================================================
"""Декораторы для регистрации провайдеров.

Предоставляет декларативный API для регистрации адаптеров провайдеров.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from bioetl.composition.providers.provider_registry import (
    AdapterCreator,
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import DataSourcePort

T = TypeVar("T", bound="DataSourcePort")


def register_provider(
    name: str,
    *,
    http_rate: float = 5.0,
    http_capacity: int = 10,
    requires_http_client: bool = True,
    requires_logger: bool = True,
    rate_overrides: dict[str, float] | None = None,
    custom_creator: AdapterCreator | None = None,
    **default_kwargs: Any,
) -> Callable[[type[T]], type[T]]:
    """Декоратор для регистрации провайдера данных.

    Регистрирует класс адаптера в ProviderRegistry при импорте модуля.

    Args:
        name: Уникальное имя провайдера (например, "chembl", "pubchem")
        http_rate: Rate limit для HTTP клиента (requests/second)
        http_capacity: Ёмкость token bucket
        requires_http_client: Нужен ли HTTP клиент для инициализации
        requires_logger: Нужен ли логгер для инициализации
        rate_overrides: Условные переопределения rate limit.
            Ключ — имя атрибута Settings, значение — новый rate.
        custom_creator: Кастомная функция создания адаптера.
            Если указана, используется вместо стандартной логики.
        **default_kwargs: Дефолтные kwargs для конструктора адаптера

    Returns:
        Декоратор класса

    Example:
        >>> @register_provider(
        ...     "chembl",
        ...     http_rate=10.0,
        ...     http_capacity=20,
        ... )
        ... class ChemblAdapter:
        ...     def __init__(self, http_client, logger=None):
        ...         ...

        >>> # Для провайдеров со сложной логикой инициализации:
        >>> def create_pubmed(http_client, logger, settings, **kwargs):
        ...     api_key = kwargs.get("api_key") or settings.pubmed_api_key
        ...     return PubMedAdapter(http_client, logger, api_key=api_key)
        >>>
        >>> @register_provider(
        ...     "pubmed",
        ...     http_rate=3.0,
        ...     rate_overrides={"pubmed_api_key": 10.0},
        ...     custom_creator=create_pubmed,
        ... )
        ... class PubMedAdapter:
        ...     ...
    """

    def decorator(cls: type[T]) -> type[T]:
        """Inner decorator that performs provider registration.

        Captures configuration from the outer scope and registers the
        decorated class with ProviderRegistry. Also injects __provider_name__
        attribute for runtime introspection.

        Args:
            cls: The adapter class being decorated.

        Returns:
            The original class unchanged (registration is a side effect).

        Side effects:
            - Registers provider in ProviderRegistry with captured config
            - Adds __provider_name__ attribute to the class
        """
        # Создаём HTTP конфигурацию
        http_config: HttpConfig | None = None
        if requires_http_client:
            http_config = HttpConfig(
                rate=http_rate,
                capacity=http_capacity,
                rate_overrides=rate_overrides or {},
            )

        # Создаём конфигурацию провайдера
        config = ProviderConfig(
            adapter_class=cls,
            http_config=http_config,
            requires_http_client=requires_http_client,
            requires_logger=requires_logger,
            default_kwargs=dict(default_kwargs),
            custom_creator=custom_creator,
        )

        # Регистрируем провайдера
        ProviderRegistry.register(name, config)

        # Сохраняем имя провайдера в классе для интроспекции
        cls.__provider_name__ = name  # type: ignore[attr-defined]

        return cls

    return decorator

================================================================================
File: loader.py
Path: providers\loader.py
================================================================================
"""Provider loader module.

Ensures all providers are registered in ProviderRegistry.
Called from bootstrap.py for initialization.
"""

from __future__ import annotations

from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.composition.providers.registration import register_all_providers

_loaded = False


def load_providers(force: bool = False) -> None:
    """Load and register all providers.

    This function should be called once at application startup
    (e.g., in bootstrap.py) to initialize ProviderRegistry.

    Idempotent - repeated calls are safe (if force=False).

    Args:
        force: If True, re-register providers even if already loaded.
            Used in tests to reset state.

    Example:
        >>> from bioetl.composition.providers import load_providers
        >>> load_providers()
        >>> # Now ProviderRegistry is ready
        >>> from bioetl.composition.providers import ProviderRegistry
        >>> config = ProviderRegistry.get("chembl")

    """
    global _loaded

    if _loaded and not force:
        return

    if force:
        # Clear registry before re-registration
        ProviderRegistry.clear()

    # Explicit registration of all providers
    register_all_providers()

    _loaded = True


def ensure_providers_loaded() -> None:
    """Ensure providers are loaded.

    Convenience function for use in places where ProviderRegistry
    must be initialized.
    """
    if not _loaded:
        load_providers()


def get_loaded_status() -> bool:
    """Return provider loading status."""
    return _loaded


def reset_loader() -> None:
    """Reset loading status. Only for tests."""
    global _loaded
    _loaded = False
    ProviderRegistry.clear()


_LOADER_API = (get_loaded_status, reset_loader)

================================================================================
File: provider_registry.py
Path: providers\provider_registry.py
================================================================================
"""Provider Registry - единый реестр провайдеров данных.

Централизует регистрацию провайдеров, устраняя необходимость
изменять несколько файлов при добавлении нового провайдера.

После унификации с DataSourceRegistry, этот модуль также отвечает за
высокоуровневое создание data sources с поддержкой фильтрации.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True)
class HttpConfig:
    """Конфигурация HTTP клиента для провайдера.

    Attributes:
        rate: Базовый rate limit (requests/second)
        capacity: Ёмкость token bucket
        rate_overrides: Условные переопределения rate limit.
            Ключ — имя атрибута Settings (например, "pubmed_api_key"),
            значение — новый rate при наличии этого атрибута.
    """

    rate: float = 5.0
    capacity: int = 10
    rate_overrides: dict[str, float] = field(default_factory=dict)


# Type alias для low-level adapter creator
AdapterCreator = Callable[..., "DataSourcePort"]


class DataSourceCreator(Protocol):
    """Protocol for high-level data source creator functions.

    These functions create fully configured data sources with filtering support.
    """

    def __call__(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create a configured data source.

        Args:
            settings: Application settings
            pipeline_config: Pipeline configuration from YAML
            logger: LoggerPort instance for structured logging
            filter_config: Optional filter configuration
            metrics: Optional metrics port for recording filter statistics
            pipeline_name: Pipeline name for metrics labels

        Returns:
            Configured DataSourcePort instance
        """
        ...


@dataclass(frozen=True)
class ProviderConfig:
    """Полная конфигурация провайдера.

    Attributes:
        adapter_class: Класс адаптера, реализующий DataSourcePort
        http_config: Конфигурация HTTP клиента (None если провайдер
            управляет своим клиентом самостоятельно)
        requires_http_client: Нужен ли HTTP клиент для инициализации
        requires_logger: Нужен ли логгер для инициализации
        default_kwargs: Дополнительные kwargs для конструктора адаптера
        custom_creator: Кастомная функция создания адаптера для
            сложных случаев (например, PubMed с API key логикой)
        data_source_creator: Высокоуровневая функция создания data source
            с поддержкой фильтрации. Если указана, используется вместо
            стандартной логики в create_data_source().
    """

    adapter_class: type[DataSourcePort]
    http_config: HttpConfig | None = None
    requires_http_client: bool = True
    requires_logger: bool = True
    default_kwargs: dict[str, Any] = field(default_factory=dict)
    custom_creator: AdapterCreator | None = None
    data_source_creator: DataSourceCreator | None = None


class ProviderRegistry:
    """Единый реестр провайдеров данных.

    Централизует:
    - Регистрацию адаптеров провайдеров
    - Конфигурацию HTTP клиентов
    - Создание экземпляров адаптеров

    Example:
        >>> from bioetl.composition.providers import ProviderRegistry, register_provider
        >>>
        >>> @register_provider("mydb", http_rate=10.0)
        ... class MyDBAdapter:
        ...     pass
        >>>
        >>> adapter = ProviderRegistry.create_adapter("mydb", http_client=client)
    """

    _providers: ClassVar[dict[str, ProviderConfig]] = {}

    @classmethod
    def register(cls, name: str, config: ProviderConfig) -> None:
        """Регистрирует провайдера.

        При повторной регистрации того же провайдера конфигурация перезаписывается.
        Это позволяет корректно работать при reload модулей.

        Args:
            name: Уникальное имя провайдера (например, "chembl", "pubchem")
            config: Конфигурация провайдера
        """
        cls._providers[name] = config

    @classmethod
    def get(cls, name: str) -> ProviderConfig:
        """Возвращает конфигурацию провайдера.

        Args:
            name: Имя провайдера

        Returns:
            Конфигурация провайдера

        Raises:
            KeyError: Если провайдер не зарегистрирован
        """
        if name not in cls._providers:
            available = ", ".join(sorted(cls._providers.keys()))
            raise KeyError(f"Unknown provider: {name}. Available: {available}")
        return cls._providers[name]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Проверяет, зарегистрирован ли провайдер.

        Args:
            name: Имя провайдера

        Returns:
            True если провайдер зарегистрирован
        """
        return name in cls._providers

    @classmethod
    def create_adapter(
        cls,
        name: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        **kwargs: Any,
    ) -> DataSourcePort:
        """Создаёт экземпляр адаптера провайдера.

        Args:
            name: Имя провайдера
            http_client: HTTP клиент (требуется для провайдеров с requires_http_client=True)
            logger: Логгер (требуется для провайдеров с requires_logger=True)
            settings: Настройки приложения (для кастомных creators)
            **kwargs: Дополнительные аргументы для конструктора

        Returns:
            Экземпляр адаптера, реализующий DataSourcePort

        Raises:
            KeyError: Если провайдер не зарегистрирован
            ValueError: Если требуемый http_client или logger не передан
        """
        config = cls.get(name)

        # Use custom creator if available
        if config.custom_creator:
            return config.custom_creator(
                http_client=http_client,
                logger=logger,
                settings=settings,
                **kwargs,
            )

        # Standard creation logic
        init_kwargs: dict[str, Any] = {**config.default_kwargs, **kwargs}

        if config.requires_http_client:
            if http_client is None:
                raise ValueError(
                    f"Provider '{name}' requires http_client but none was provided. "
                    "Ensure http_client is passed from Composition Root."
                )
            init_kwargs["http_client"] = http_client

        if config.requires_logger:
            if logger is None:
                raise ValueError(
                    f"Provider '{name}' requires logger but none was provided. "
                    "Ensure logger is passed from Composition Root."
                )
            init_kwargs["logger"] = logger

        return config.adapter_class(**init_kwargs)

    @classmethod
    def get_http_config(cls, name: str) -> HttpConfig | None:
        """Возвращает HTTP конфигурацию провайдера.

        Args:
            name: Имя провайдера

        Returns:
            HttpConfig или None если провайдер не использует общий HTTP клиент
        """
        config = cls.get(name)
        return config.http_config

    @classmethod
    def create_data_source(
        cls,
        name: str,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Создаёт полностью настроенный data source с поддержкой фильтрации.

        Высокоуровневый метод, объединяющий функциональность ProviderRegistry
        и бывшего DataSourceRegistry. Использует data_source_creator из
        конфигурации провайдера, если он указан.

        Args:
            name: Имя провайдера
            settings: Настройки приложения
            pipeline_config: Конфигурация пайплайна из YAML
            logger: LoggerPort для структурированного логирования
            filter_config: Опциональная конфигурация фильтрации
            metrics: Опциональный MetricsPort для статистики
            pipeline_name: Имя пайплайна для меток метрик

        Returns:
            Настроенный DataSourcePort с поддержкой фильтрации

        Raises:
            KeyError: Если провайдер не зарегистрирован
            ValueError: Если data_source_creator не задан для провайдера
        """
        config = cls.get(name)

        if config.data_source_creator is None:
            raise ValueError(
                f"Provider '{name}' does not have a data_source_creator configured. "
                "Register the provider with a data_source_creator in registration.py."
            )

        return config.data_source_creator(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )

    @classmethod
    def has_data_source_creator(cls, name: str) -> bool:
        """Проверяет, есть ли у провайдера data_source_creator.

        Args:
            name: Имя провайдера

        Returns:
            True если провайдер имеет data_source_creator
        """
        if not cls.is_registered(name):
            return False
        config = cls.get(name)
        return config.data_source_creator is not None

    @classmethod
    def list_providers(cls) -> list[str]:
        """Список всех зарегистрированных провайдеров.

        Returns:
            Отсортированный список имён провайдеров
        """
        return sorted(cls._providers.keys())

    @classmethod
    def clear(cls) -> None:
        """Очищает реестр. Используется для тестов."""
        cls._providers.clear()

================================================================================
File: registration.py
Path: providers\registration.py
================================================================================
"""Explicit provider registration for Composition layer.

Loads config from configs/sources/*.yaml. HttpConfig serves as fallback.
Config helpers extracted to _config_helpers.py per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from bioetl.application.core.idmapping_data_source import IDMappingDataSource
from bioetl.application.core.publication_term_data_source import (
    PublicationTermDataSource,
)
from bioetl.composition.providers._config_helpers import (
    _get_adapter_config,
    _get_batch_size_from_config,
    _get_circuit_breaker_from_config,
    _get_factories,
    _get_rate_limit_from_config,
    _wrap_with_filter,
)
from bioetl.composition.providers.provider_registry import (
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)
from bioetl.domain.models.filter import ExtractionParams

# Import adapter classes from Infrastructure (allowed direction)
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefAdapter,
    _create_crossref_adapter,
)
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.openalex.client import (
    OpenAlexAdapter,
    _create_openalex_adapter,
)
from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter
from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    PubMedAdapter,
    _create_pubmed_adapter,
)
from bioetl.infrastructure.adapters.semanticscholar.adapter import (
    SemanticScholarAdapter,
)
from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter
from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
    UniProtIDMappingClient,
)

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _validate_extraction_input_filter_overlap(
    extraction_params: ExtractionParams,
    input_filter: InputFilterConfig,
    logger: LoggerPort,
) -> None:
    """Warn if input_filter field overlaps extraction_params keys.

    Both are applied as AND in API query. Overlap means one might
    shadow the other. Log WARNING but do not block.
    """
    if not input_filter.enabled or extraction_params.is_empty:
        return

    filter_field = input_filter.filter_field
    if filter_field and filter_field in extraction_params.params:
        logger.warning(
            "extraction_params_input_filter_overlap",
            overlap_field=filter_field,
            extraction_value=str(extraction_params.params[filter_field]),
            resolution="input_filter will override extraction_params for this field",
        )

    # Check multi-column mode
    if input_filter.columns:
        for col in input_filter.columns:
            if col.filter_field in extraction_params.params:
                logger.warning(
                    "extraction_params_input_filter_overlap",
                    overlap_field=col.filter_field,
                    extraction_value=str(extraction_params.params[col.filter_field]),
                    resolution="input_filter will override",
                )


def _create_chembl_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create ChEMBL data source with optional CSV filtering.

    Configuration is loaded from configs/sources/chembl.yaml via AdapterConfig.
    This ensures YAML is the single source of truth (RULES.md §12.1.2).

    For document_term entity type, wraps the adapter with PublicationTermDataSource
    to extract terms from publication records (derived entity pattern).
    """
    DataSourceFactory, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("chembl", settings)

    # Load adapter configuration from YAML (single source of truth)
    adapter_config = _get_adapter_config("chembl", default_page_size=1000)

    # Build ExtractionParams from pipeline config (ADR-028 §3)
    extraction_params = ExtractionParams(params=pipeline_config.extraction_params)

    # Validate overlap between extraction_params and input_filter
    if filter_config is not None:
        _validate_extraction_input_filter_overlap(
            extraction_params, filter_config, logger
        )

    base_adapter = DataSourceFactory.create(
        "chembl",
        http_client=http_client,
        logger=logger,
        adapter_config=adapter_config,
        metrics=metrics,
        extraction_params=extraction_params,
    )

    # Wrap with PublicationTermDataSource for derived entity extraction
    # publication_term is extracted from publication records (1:M relationship)
    if pipeline_config.entity_type == "publication_term":
        base_adapter = PublicationTermDataSource(base_adapter)

    return _wrap_with_filter(
        base_adapter, filter_config, logger, metrics, pipeline_name
    )


def _create_pubchem_adapter(
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: Settings | None = None,
    **kwargs: Any,
) -> DataSourcePort:
    """Create PubChem adapter with all dependencies injected from Composition Root."""
    if logger is None:
        raise ValueError("PubChem adapter requires logger")

    rate_limit = _get_rate_limit_from_config("pubchem")
    cb_config = _get_circuit_breaker_from_config("pubchem")

    rate = kwargs.pop("rate", rate_limit.rate)
    capacity = kwargs.pop("capacity", rate_limit.capacity)
    cb_threshold = kwargs.pop("circuit_breaker_threshold", cb_config.failure_threshold)
    cb_timeout = kwargs.pop("circuit_breaker_timeout", cb_config.recovery_timeout)
    max_workers = kwargs.pop("max_workers", 4)
    strict_error_handling = kwargs.pop("strict_error_handling", False)
    metrics = kwargs.pop("metrics", None)

    return PubChemAdapter(
        logger=logger,
        rate_limiter=TokenBucket(rate=rate, capacity=capacity, provider="pubchem"),
        circuit_breaker=CircuitBreaker(
            provider="pubchem",
            failure_threshold=cb_threshold,
            recovery_timeout=cb_timeout,
            metrics=metrics,
        ),
        thread_pool=ThreadPoolExecutor(max_workers=max_workers),
        strict_error_handling=strict_error_handling,
    )


def _create_pubchem_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create PubChem data source with optional CSV filtering."""
    data_source = _create_pubchem_adapter(
        logger=logger,
        settings=settings,
        strict_error_handling=settings.strict_error_handling,
        metrics=metrics,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_uniprot_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create UniProt data source with optional CSV filtering."""
    DataSourceFactory, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("uniprot", settings)
    data_source = DataSourceFactory.create(
        "uniprot",
        http_client=http_client,
        logger=logger,
        base_url=pipeline_config.source.api.base_url or "https://rest.uniprot.org",
        strict_error_handling=settings.strict_error_handling,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_pubmed_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create PubMed data source with optional CSV filtering."""
    _, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("pubmed", settings)

    # Determine API key: config takes precedence over settings
    configured_api_key = pipeline_config.source.api_key
    settings_api_key = (
        settings.pubmed_api_key.get_secret_value() if settings.pubmed_api_key else None
    )
    api_key = configured_api_key or settings_api_key

    email = pipeline_config.source.email or settings.default_email

    data_source = PubMedAdapter(
        http_client=http_client,
        logger=logger,
        email=email,
        api_key=api_key,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_crossref_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create CrossRef data source with optional CSV filtering.

    CrossRef requires mailto for polite pool access (50 req/sec vs 1 req/sec).
    Email is obtained from pipeline config or settings.default_email.

    Args:
        settings: Application settings.
        pipeline_config: Pipeline configuration from YAML.
        logger: LoggerPort for structured logging.
        filter_config: Optional filter configuration for CSV-based DOI filtering.
        metrics: Optional MetricsPort for recording adapter metrics.
        pipeline_name: Pipeline name for metrics labels.

    Returns:
        Configured DataSourcePort with optional filtering wrapper.

    Raises:
        ValueError: If mailto is not configured in settings or pipeline config.

    """
    _, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("crossref", settings)

    # Get mailto from pipeline config or settings
    mailto = pipeline_config.source.email or settings.default_email
    batch_size = _get_batch_size_from_config("crossref", default=50)

    data_source = _create_crossref_adapter(
        http_client=http_client,
        logger=logger,
        settings=settings,
        mailto=mailto,
        batch_size=batch_size,
        metrics=metrics,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_openalex_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create OpenAlex data source with optional CSV filtering.

    OpenAlex requires mailto for polite pool access (10 req/sec).
    Email is obtained from pipeline config or settings.default_email.

    Args:
        settings: Application settings.
        pipeline_config: Pipeline configuration from YAML.
        logger: LoggerPort for structured logging.
        filter_config: Optional filter configuration for CSV-based DOI filtering.
        metrics: Optional MetricsPort for recording adapter metrics.
        pipeline_name: Pipeline name for metrics labels.

    Returns:
        Configured DataSourcePort with optional filtering wrapper.

    Raises:
        ValueError: If mailto is not configured in settings or pipeline config.

    """
    _, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("openalex", settings)

    # Get mailto from pipeline config or settings
    mailto = pipeline_config.source.email or settings.default_email
    batch_size = _get_batch_size_from_config("openalex", default=50)

    data_source = _create_openalex_adapter(
        http_client=http_client,
        logger=logger,
        settings=settings,
        mailto=mailto,
        batch_size=batch_size,
        metrics=metrics,
    )
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_semanticscholar_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create Semantic Scholar data source with optional CSV filtering.

    Semantic Scholar requires API key for stable rate limits (1 req/sec).
    API key is obtained from settings.semanticscholar_api_key.

    Args:
        settings: Application settings.
        pipeline_config: Pipeline configuration from YAML.
        logger: LoggerPort for structured logging.
        filter_config: Optional filter configuration for CSV-based DOI filtering.
        metrics: Optional MetricsPort for recording adapter metrics.
        pipeline_name: Pipeline name for metrics labels.

    Returns:
        Configured DataSourcePort with optional filtering wrapper.

    """
    _, HttpClientFactory = _get_factories()
    http_client = HttpClientFactory.create_for_provider("semanticscholar", settings)

    # Get API key from settings (configured via BIOETL_SEMANTICSCHOLAR_API_KEY env var)
    api_key = (
        settings.semanticscholar_api_key.get_secret_value()
        if settings.semanticscholar_api_key
        else ""
    )
    if not api_key:
        logger.warning(
            "semanticscholar_no_api_key",
            message="No API key provided. Rate limits will be shared with other users.",
        )

    batch_size = _get_batch_size_from_config("semanticscholar", default=100)

    data_source = SemanticScholarAdapter(
        http_client=http_client,
        logger=logger,
        api_key=api_key,
        batch_size=batch_size,
        metrics=metrics,
    )

    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _create_uniprot_idmapping_data_source(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Create UniProt ID Mapping data source.

    Creates an IDMappingDataSource that:
    1. Reads ChEMBL target IDs from input CSV file
    2. Calls UniProt ID Mapping API to map to UniProt accessions
    3. Yields records with mapping results

    Args:
        settings: Application settings.
        pipeline_config: Pipeline configuration from YAML.
        logger: LoggerPort for structured logging.
        filter_config: Unused (filtering happens via input_path CSV).
        metrics: Optional MetricsPort for recording adapter metrics.
        pipeline_name: Pipeline name for metrics labels.

    Returns:
        Configured IDMappingDataSource instance.
    """
    from pathlib import Path

    _, HttpClientFactory = _get_factories()

    # Create HTTP client for ID Mapping API
    http_client = HttpClientFactory.create_for_provider("uniprot", settings)

    # Create ID Mapping client
    base_url = "https://rest.uniprot.org"
    if pipeline_config.source.api and pipeline_config.source.api.base_url:
        base_url = pipeline_config.source.api.base_url
    idmapping_client = UniProtIDMappingClient(
        http_client=http_client,
        logger=logger,
        metrics=metrics,
        base_url=base_url,
    )

    # Get input path from pipeline config
    input_path_str = (
        pipeline_config.source.input_path
        if hasattr(pipeline_config.source, "input_path")
        else "data/input/target.csv"
    )
    input_path = Path(input_path_str)

    # Get database names from API config
    from_db = "ChEMBL"
    to_db = "UniProtKB"
    if pipeline_config.source.api:
        from_db = getattr(pipeline_config.source.api, "from_db", from_db)
        to_db = getattr(pipeline_config.source.api, "to_db", to_db)

    # Extract seed IDs from filter_config (composite mode)
    seed_ids: list[str] | None = None
    if filter_config and filter_config.direct_filter_ids:
        seed_ids = list(filter_config.direct_filter_ids)

    return IDMappingDataSource(
        idmapping_client=idmapping_client,
        input_path=input_path,
        logger=logger,
        from_db=from_db,
        to_db=to_db,
        seed_ids=seed_ids,
    )


# =============================================================================
# Provider registration
# =============================================================================


def register_all_providers() -> None:
    """Explicitly register all data source providers.

    This function MUST be called from bootstrap before using ProviderRegistry.
    Idempotent - safe to call multiple times.

    Configuration Priority:
    1. configs/sources/{provider}.yaml - PRIMARY (rate limits, circuit breaker, batch_size)
    2. HttpConfig in ProviderConfig - FALLBACK only

    Provider configurations are now loaded from YAML files:
    - ChEMBL: configs/sources/chembl.yaml
    - PubChem: configs/sources/pubchem.yaml
    - UniProt: configs/sources/uniprot.yaml
    - PubMed: configs/sources/pubmed.yaml
    - CrossRef: configs/sources/crossref.yaml
    - OpenAlex: configs/sources/openalex.yaml
    - Semantic Scholar: configs/sources/semanticscholar.yaml

    Each provider includes a data_source_creator for unified registry access.
    """
    # Load rate limits from source configs (with fallback defaults)
    chembl_rate_limit = _get_rate_limit_from_config("chembl")
    pubchem_rate_limit = _get_rate_limit_from_config("pubchem")
    uniprot_rate_limit = _get_rate_limit_from_config("uniprot")
    pubmed_rate_limit = _get_rate_limit_from_config("pubmed")
    crossref_rate_limit = _get_rate_limit_from_config("crossref")

    # ChEMBL - async HTTP adapter
    if not ProviderRegistry.is_registered("chembl"):
        ProviderRegistry.register(
            "chembl",
            ProviderConfig(
                adapter_class=ChemblAdapter,
                http_config=HttpConfig(
                    rate=chembl_rate_limit.rate,
                    capacity=chembl_rate_limit.capacity,
                ),
                requires_http_client=True,
                requires_logger=True,
                data_source_creator=_create_chembl_data_source,
            ),
        )

    # PubChem - sync adapter with DI-compliant custom creator
    # Dependencies (TokenBucket, CircuitBreaker, ThreadPoolExecutor) are created
    # in _create_pubchem_adapter following Composition Root pattern
    if not ProviderRegistry.is_registered("pubchem"):
        ProviderRegistry.register(
            "pubchem",
            ProviderConfig(
                adapter_class=PubChemAdapter,
                http_config=HttpConfig(
                    rate=pubchem_rate_limit.rate,
                    capacity=pubchem_rate_limit.capacity,
                ),
                requires_http_client=False,
                requires_logger=True,
                custom_creator=_create_pubchem_adapter,
                data_source_creator=_create_pubchem_data_source,
            ),
        )

    # UniProt - async HTTP adapter with conditional rate override
    if not ProviderRegistry.is_registered("uniprot"):
        ProviderRegistry.register(
            "uniprot",
            ProviderConfig(
                adapter_class=UniProtAdapter,
                http_config=HttpConfig(
                    rate=uniprot_rate_limit.rate,
                    capacity=uniprot_rate_limit.capacity,
                    rate_overrides={"uniprot_api_key": 100.0},
                ),
                requires_http_client=True,
                requires_logger=True,
                data_source_creator=_create_uniprot_data_source,
            ),
        )

    # PubMed - async HTTP adapter with custom creator for email/API key handling
    if not ProviderRegistry.is_registered("pubmed"):
        ProviderRegistry.register(
            "pubmed",
            ProviderConfig(
                adapter_class=PubMedAdapter,
                http_config=HttpConfig(
                    rate=pubmed_rate_limit.rate,
                    capacity=pubmed_rate_limit.capacity,
                    rate_overrides={"pubmed_api_key": 10.0},
                ),
                requires_http_client=True,
                requires_logger=True,
                custom_creator=_create_pubmed_adapter,
                data_source_creator=_create_pubmed_data_source,
            ),
        )

    # CrossRef - async HTTP adapter for DOI resolution and publication metadata
    # Requires mailto for polite pool access (50 req/sec vs 1 req/sec without)
    if not ProviderRegistry.is_registered("crossref"):
        ProviderRegistry.register(
            "crossref",
            ProviderConfig(
                adapter_class=CrossRefAdapter,
                http_config=HttpConfig(
                    rate=crossref_rate_limit.rate,
                    capacity=crossref_rate_limit.capacity,
                ),
                requires_http_client=True,
                requires_logger=True,
                custom_creator=_create_crossref_adapter,
                data_source_creator=_create_crossref_data_source,
            ),
        )

    # OpenAlex - async HTTP adapter for open scholarly metadata
    # Requires mailto for polite pool access (10 req/sec)
    # Supports batch DOI resolution with title fallback
    openalex_rate_limit = _get_rate_limit_from_config("openalex")
    if not ProviderRegistry.is_registered("openalex"):
        ProviderRegistry.register(
            "openalex",
            ProviderConfig(
                adapter_class=OpenAlexAdapter,
                http_config=HttpConfig(
                    rate=openalex_rate_limit.rate,
                    capacity=openalex_rate_limit.capacity,
                ),
                requires_http_client=True,
                requires_logger=True,
                custom_creator=_create_openalex_adapter,
                data_source_creator=_create_openalex_data_source,
            ),
        )

    # Semantic Scholar - async HTTP adapter for DOI resolution with title fallback
    # API key recommended for stable rate limits (1 req/sec guaranteed)
    s2_rate_limit = _get_rate_limit_from_config("semanticscholar")
    if not ProviderRegistry.is_registered("semanticscholar"):
        ProviderRegistry.register(
            "semanticscholar",
            ProviderConfig(
                adapter_class=SemanticScholarAdapter,
                http_config=HttpConfig(
                    rate=s2_rate_limit.rate,
                    capacity=s2_rate_limit.capacity,
                ),
                requires_http_client=True,
                requires_logger=True,
                data_source_creator=_create_semanticscholar_data_source,
            ),
        )

    # UniProt ID Mapping - maps ChEMBL target IDs to UniProt accessions
    # Uses UniProt ID Mapping REST API (job-based async)
    # Input comes from CSV file, not external API filtering
    # Note: IDMappingDataSource is a lightweight wrapper, actual API client is
    # UniProtIDMappingClient created in the data_source_creator
    uniprot_idmapping_rate_limit = _get_rate_limit_from_config("uniprot")
    if not ProviderRegistry.is_registered("uniprot_idmapping"):
        ProviderRegistry.register(
            "uniprot_idmapping",
            ProviderConfig(
                adapter_class=IDMappingDataSource,
                http_config=HttpConfig(
                    rate=uniprot_idmapping_rate_limit.rate,
                    capacity=uniprot_idmapping_rate_limit.capacity,
                ),
                requires_http_client=True,
                requires_logger=True,
                data_source_creator=_create_uniprot_idmapping_data_source,
            ),
        )

================================================================================
File: registry.py
Path: registry.py
================================================================================
"""Pipeline Registry for discovering and instantiating pipelines.

MOVED to composition layer to fix dependency direction.

This module provides an instance-level PipelineRegistry for:
- Test isolation (each test can have its own registry)
- Parallel test execution without clear()
- Proper DI through composition root

A default global instance is provided for backward compatibility.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol, runtime_checkable

import pyarrow as pa

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@runtime_checkable
class PipelineFactoryProtocol(Protocol):
    """Protocol for pipeline factories."""

    pipeline_name: str
    silver_schema: pa.Schema | None
    pandera_silver_schema: Any

    def create_with_services(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = ...,
        filter_config: InputFilterConfig | None = ...,
        tracer: TracingPort | None = ...,
        dq_monitor: DQMonitorPort | None = ...,
        metrics: MetricsPort | None = ...,
        cached_bronze: CachedBronzeContext | None = ...,
    ) -> BasePipeline:
        """Create pipeline with services."""
        ...

    def create_runner(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        observability: ObservabilityBundle,
        filter_config: InputFilterConfig | None = None,
        config: PipelineYamlConfig | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> PipelineRunner:
        """Create pipeline runner."""
        ...


class PipelineDefinition(NamedTuple):
    """Definition of a registered pipeline."""

    factory: PipelineFactoryProtocol
    """Factory instance."""

    silver_schema: pa.Schema | None
    """PyArrow schema for Silver layer validation."""

    gold_schema: Any
    """Pandera schema for Gold layer validation (required)."""

    pandera_silver_schema: Any = None
    """Pandera DataFrameModel class for Silver layer validation."""


class PipelineRegistry:
    """Registry for pipeline factories.

    Thread-safe instance-level registry for pipeline factory instances.
    All public methods are protected with RLock for concurrent access.

    This class can be instantiated for test isolation or used via the
    default global instance for backward compatibility.

    Example (instance-level for tests):
        >>> registry = PipelineRegistry()
        >>> factory = GenericPipelineFactory(...)
        >>> registry.register_factory(factory)

    Example (backward-compatible class method API):
        >>> factory = GenericPipelineFactory(...)
        >>> PipelineRegistry.register_factory(factory)  # Uses default instance
    """

    def __init__(self) -> None:
        """Initialize a new empty registry."""
        self._registry: dict[str, PipelineDefinition] = {}
        self._lock = threading.RLock()

    def register_factory(
        self,
        factory: PipelineFactoryProtocol,
    ) -> None:
        """Register a pipeline factory instance.

        Thread-safe registration with duplicate detection.

        Args:
            factory: Factory instance with pipeline_name and silver_schema attributes

        Raises:
            ValueError: If factory does not have gold_schema attribute
            ValueError: If pipeline is already registered (prevents double registration)
        """
        gold_schema = getattr(factory, "gold_schema", None)
        if gold_schema is None:
            raise ValueError(
                f"Factory '{factory.pipeline_name}' must have gold_schema. "
                "All Gold layer writes require schema validation."
            )

        with self._lock:
            if factory.pipeline_name in self._registry:
                raise ValueError(
                    f"Pipeline already registered: {factory.pipeline_name}. "
                    "Use a new registry instance or clear() for tests."
                )
            self._registry[factory.pipeline_name] = PipelineDefinition(
                factory=factory,
                silver_schema=factory.silver_schema,
                gold_schema=gold_schema,
                pandera_silver_schema=getattr(factory, "pandera_silver_schema", None),
            )

    def get(self, pipeline_name: str) -> PipelineDefinition:
        """Get pipeline definition by name.

        Thread-safe read access to registry.

        Args:
            pipeline_name: Pipeline identifier

        Returns:
            PipelineDefinition with factory and schema

        Raises:
            RuntimeError: If registry is empty (registration not called)
            ValueError: If pipeline is not registered
        """
        with self._lock:
            if not self._registry:
                raise RuntimeError(
                    "PipelineRegistry is empty. "
                    "Did you forget to call register_all_pipelines()?"
                )
            if pipeline_name not in self._registry:
                raise ValueError(
                    f"Unknown pipeline name: {pipeline_name}. "
                    f"Available: {sorted(self._registry.keys())}"
                )
            return self._registry[pipeline_name]

    def list_pipelines(self) -> list[str]:
        """List all registered pipeline names.

        Thread-safe listing with deterministic ordering.
        Returns a snapshot of keys sorted alphabetically.

        Returns:
            Sorted list of pipeline names (deterministic order).
        """
        with self._lock:
            return sorted(self._registry.keys())

    def register(
        self,
        key: str,
        value: PipelineFactoryProtocol,
    ) -> None:
        """Register a pipeline factory (unified API).

        Thread-safe registration with duplicate detection.
        This method provides a unified API consistent with other registries.
        For backward compatibility, use register_factory() which extracts
        the key from factory.pipeline_name.

        Args:
            key: Pipeline name (must match factory.pipeline_name)
            value: Pipeline factory instance

        Raises:
            ValueError: If factory does not have gold_schema attribute
            ValueError: If pipeline is already registered
        """
        gold_schema = getattr(value, "gold_schema", None)
        if gold_schema is None:
            raise ValueError(
                f"Factory '{key}' must have gold_schema. "
                "All Gold layer writes require schema validation."
            )
        with self._lock:
            if key in self._registry:
                raise ValueError(
                    f"Pipeline already registered: {key}. "
                    "Use a new registry instance or clear() for tests."
                )
            self._registry[key] = PipelineDefinition(
                factory=value,
                silver_schema=value.silver_schema,
                gold_schema=gold_schema,
                pandera_silver_schema=getattr(value, "pandera_silver_schema", None),
            )

    def list_keys(self) -> list[str]:
        """List all registered pipeline names (unified API).

        Alias for list_pipelines().
        """
        return self.list_pipelines()

    def contains(self, key: str) -> bool:
        """Check if pipeline is registered.

        Thread-safe check for key existence.

        Args:
            key: Pipeline name to check

        Returns:
            True if pipeline is registered, False otherwise
        """
        with self._lock:
            return key in self._registry

    def clear(self) -> None:
        """Clear all registrations (for testing).

        Thread-safe reset of registry state.
        WARNING: Only use in tests. Not for production.
        """
        with self._lock:
            self._registry.clear()


# Default global instance for backward compatibility
_default_registry = PipelineRegistry()


def get_default_registry() -> PipelineRegistry:
    """Get the default global registry instance.

    Use this function when you need access to the shared registry.
    For tests, prefer creating a new PipelineRegistry() instance.

    Returns:
        The default global PipelineRegistry instance.
    """
    return _default_registry


def create_registry() -> PipelineRegistry:
    """Create a new isolated registry instance.

    Use this for test isolation or when you need multiple registries
    in the same process.

    Returns:
        A new empty PipelineRegistry instance.
    """
    return PipelineRegistry()

================================================================================
File: __init__.py
Path: services\__init__.py
================================================================================
"""Composition services for cross-cutting concerns.

Services in the composition layer coordinate between layers and build
complex objects. Unlike application services, these do not contain
business logic but rather assemble components.

Services:
- MetadataCoordinator: Centralized metadata creation for Medallion layers
- Versioning utilities: Git commit, config hash, pipeline version
"""

from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_git_commit,
    get_pipeline_version,
)

# Re-export input types from domain.ports for convenience
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
)

__all__ = [
    "BronzeMetadataInput",
    "GoldMetadataInput",
    "MetadataCoordinator",
    "SilverMetadataInput",
    "compute_config_hash",
    "get_git_commit",
    "get_pipeline_version",
]

================================================================================
File: metadata_coordinator.py
Path: services\metadata_coordinator.py
================================================================================
"""Centralized Metadata Coordinator Service.

Provides a single source of truth for creating metadata across all Medallion layers.
Eliminates duplication of RuntimeMetadata, PipelineMetadata, and EnvironmentMetadata
creation logic that was previously scattered across Bronze, Silver, and Gold writers.

Implements:
- Consistent run_id and timestamps across layers
- Cached environment metadata (computed once)
- Factory methods for layer-specific metadata
- Implements MetadataCoordinatorPort from domain.ports

Architecture:
- Composition Service (not Infrastructure)
- Accepts RunContext once at initialization
- Pure Python, no I/O operations
"""

from __future__ import annotations

import inspect
import platform
import socket
from datetime import datetime
from functools import cached_property
from typing import Any, Literal

from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    BronzeMetadata,
    BronzeOutputExt,
    DeltaMetrics,
    DQSummary,
    EnvironmentMetadata,
    FileOutputMetadata,
    GoldMetadata,
    GoldOutputExt,
    LineageMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SCDMetadata,
    SchemaColumnMetadata,
    SchemaMetadata,
    SilverMetadata,
    SilverOutputExt,
    SourceMetadata,
)
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
)
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.run_context import RunContext


def _get_bioetl_version() -> str:
    """Get BioETL package version.

    Returns:
        Package version string.

    Raises:
        PackageNotFoundError: If bioetl package is not installed.
    """
    from importlib.metadata import version as pkg_version

    return pkg_version("bioetl")


class MetadataCoordinator:
    """Centralized coordinator for metadata creation across Medallion layers.

    Creates consistent metadata with shared run_id, timestamps, and pipeline
    identification. Environment metadata is computed once and cached.

    Example:
        >>> from datetime import UTC, datetime
        >>> from uuid import uuid4
        >>> context = RunContext.create(
        ...     run_id=RunID(uuid4()),
        ...     run_type=RunType.INCREMENTAL,
        ...     started_at=datetime.now(UTC),
        ...     provider="chembl",
        ...     entity="activity",
        ... )
        >>> coordinator = MetadataCoordinator(context)
        >>> bronze_input = BronzeMetadataInput(...)
        >>> metadata = coordinator.create_bronze_metadata(bronze_input)
    """

    # Class-level cache for environment metadata (shared across instances)
    _cached_environment: EnvironmentMetadata | None = None

    def __init__(self, run_context: RunContext) -> None:
        """Initialize coordinator with run context.

        Args:
            run_context: Immutable context for the pipeline run.
        """
        self._context = run_context

    @property
    def run_context(self) -> RunContext:
        """Access the run context."""
        return self._context

    @cached_property
    def _run_type_enum(self) -> RunTypeEnum:
        """Map domain RunType to metadata RunTypeEnum."""
        mapping = {
            RunType.INCREMENTAL: RunTypeEnum.INCREMENTAL,
            RunType.BACKFILL: RunTypeEnum.BACKFILL,
            RunType.REBUILD: RunTypeEnum.REBUILD,
        }
        return mapping.get(self._context.run_type, RunTypeEnum.INCREMENTAL)

    @classmethod
    def _get_environment_metadata(cls) -> EnvironmentMetadata:
        """Get cached environment metadata (computed once per process).

        Environment metadata (hostname, python_version, bioetl_version) is
        immutable during process lifetime, so we cache it at class level.
        """
        if cls._cached_environment is None:
            cls._cached_environment = EnvironmentMetadata(
                hostname=socket.gethostname(),
                python_version=platform.python_version(),
                bioetl_version=_get_bioetl_version(),
            )
        return cls._cached_environment

    def _build_runtime_metadata(
        self,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> RuntimeMetadata:
        """Build RuntimeMetadata with consistent run_id and run_type.

        Args:
            started_at: Override start time (defaults to context.started_at).
            completed_at: Completion timestamp.
            duration_seconds: Operation duration.

        Returns:
            RuntimeMetadata with run context data.
        """
        return RuntimeMetadata(
            run_id=str(self._context.run_id),
            run_type=self._run_type_enum,
            started_at_utc=started_at or self._context.started_at,
            completed_at_utc=completed_at,
            duration_seconds=duration_seconds,
        )

    def _build_pipeline_metadata(self) -> PipelineMetadata:
        """Build PipelineMetadata with versioning from run context."""
        return PipelineMetadata(
            name=self._context.pipeline_name,
            provider=self._context.provider,
            entity=self._context.entity,
            version=self._context.pipeline_version or "1.0.0",
            git_commit=self._context.git_commit,
            config_hash=self._context.config_hash,
        )

    def create_bronze_metadata(self, input_data: BronzeMetadataInput) -> BronzeMetadata:
        """Create Bronze layer metadata.

        Args:
            input_data: Bronze-specific metadata inputs.

        Returns:
            Complete BronzeMetadata for sidecar file.
        """
        duration = (input_data.completed_at - input_data.started_at).total_seconds()

        # Build source metadata with query_string
        if input_data.source_metadata is not None:
            source = input_data.source_metadata
            # Inject query_string if provided and not already set in source_metadata
            if input_data.query_string and source.query_string is None:
                source = source.model_copy(
                    update={"query_string": input_data.query_string}
                )
        else:
            # Create minimal SourceMetadata with query_string
            source = SourceMetadata(
                type="api",
                query_string=input_data.query_string,
            )

        # Build file metadata for output_ext
        file_metadata = FileOutputMetadata(
            path=input_data.output_path,
            size_bytes=input_data.compressed_size,
            record_count=input_data.record_count,
        )

        return BronzeMetadata(
            runtime=self._build_runtime_metadata(
                started_at=input_data.started_at,
                completed_at=input_data.completed_at,
                duration_seconds=duration,
            ),
            pipeline=self._build_pipeline_metadata(),
            source=source,
            output=BaseOutputMetadata(
                record_count=input_data.record_count,
                total_bytes=input_data.compressed_size,
                write_started_at=input_data.started_at,
                write_completed_at=input_data.completed_at,
            ),
            output_ext=BronzeOutputExt(
                files=[file_metadata],
            ),
            environment=self._get_environment_metadata(),
            governance=input_data.governance,
        )

    def create_silver_metadata(self, input_data: SilverMetadataInput) -> SilverMetadata:
        """Create Silver layer metadata.

        Args:
            input_data: Silver-specific metadata inputs.

        Returns:
            Complete SilverMetadata for sidecar file.
        """
        if not input_data.records:
            raise ValueError("Cannot create Silver metadata without records")

        # Build lineage from records and bronze_refs
        source_batch_ids = list(
            {
                r.get("_source_batch_id", "")
                for r in input_data.records
                if r.get("_source_batch_id")
            }
        )

        bronze_paths: list[str] = []
        if input_data.bronze_refs:
            bronze_paths = [ref.relative_path for ref in input_data.bronze_refs]

        # Get transform info: prioritize input_data, fallback to RunContext
        transform_version = (
            input_data.transform_version
            if input_data.transform_version is not None
            else self._context.transform_version
        )
        transform_steps = list(
            input_data.transform_steps
            if input_data.transform_steps is not None
            else self._context.transform_steps
        )

        lineage = LineageMetadata(
            source_batch_ids=source_batch_ids,
            bronze_paths=bronze_paths,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

        # Map SilverWriteMode to DeltaMetrics operation
        operation_map: dict[
            SilverWriteMode, Literal["merge", "overwrite", "append"]
        ] = {
            SilverWriteMode.MERGE: "merge",
            SilverWriteMode.APPEND: "append",
            SilverWriteMode.DELETE: "overwrite",
        }

        delta = DeltaMetrics(
            table_path=input_data.table_path,
            operation=operation_map[input_data.mode],
            primary_key=input_data.primary_keys,
            partition_by=input_data.partition_by or [],
            version_after=input_data.version_after,
            rows_inserted=len(input_data.records),
        )

        # Build DQ summary from computed metrics or use basic fallback
        rec_count = len(input_data.records)
        dq_summary = (
            input_data.dq_metrics.to_dq_summary()
            if input_data.dq_metrics
            else DQSummary(total_records=rec_count, valid_records=rec_count)
        )

        # Calculate duration if both timestamps provided
        duration_seconds = (
            (input_data.completed_at - input_data.started_at).total_seconds()
            if input_data.started_at and input_data.completed_at
            else None
        )

        # Build unified output metadata (ADR-029)
        output = BaseOutputMetadata(
            record_count=rec_count,
            total_bytes=getattr(input_data, "total_bytes", 0),
            write_started_at=input_data.started_at,
            write_completed_at=input_data.completed_at,
        )

        # Build Silver-specific output extension with delta versions
        output_ext = SilverOutputExt(
            delta_version_before=getattr(input_data, "version_before", None),
            delta_version_after=input_data.version_after,
        )

        return SilverMetadata(
            runtime=self._build_runtime_metadata(
                started_at=input_data.started_at,
                completed_at=input_data.completed_at,
                duration_seconds=duration_seconds,
            ),
            pipeline=self._build_pipeline_metadata(),
            lineage=lineage,
            delta=delta,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            environment=self._get_environment_metadata(),
            dq_report_path=input_data.dq_report_path,
            governance=input_data.governance,
        )

    def _extract_schema_metadata(self, gold_schema: Any | None) -> SchemaMetadata:
        """Extract schema metadata from a Pandera DataFrameModel.

        Extracts contract_path, version, columns, and validation mode from
        the Pandera schema class for Gold layer metadata tracking.

        Args:
            gold_schema: Pandera DataFrameModel class (not instance).

        Returns:
            SchemaMetadata with populated fields, or default if schema is None.
        """
        if gold_schema is None:
            return SchemaMetadata()

        # Extract contract_path from module path
        contract_path: str | None = None
        try:
            module = inspect.getmodule(gold_schema)
            if module and module.__file__:
                # Convert absolute path to relative path from project root
                # e.g., .../src/bioetl/domain/contracts/gold/chembl.py
                # -> src/bioetl/domain/contracts/gold/chembl.py
                file_path = module.__file__
                if "src/bioetl" in file_path:
                    idx = file_path.find("src/bioetl")
                    contract_path = file_path[idx:]
        except Exception:
            # Module may not have __file__ or path extraction may fail
            pass

        # Extract schema version from Config if defined
        version = "1.0"
        if hasattr(gold_schema, "Config"):
            config = gold_schema.Config
            version = getattr(config, "version", "1.0")
            if not isinstance(version, str):
                version = str(version)

        # Determine validation mode
        validation: Literal["strict", "lenient"] = "strict"
        if hasattr(gold_schema, "Config"):
            config = gold_schema.Config
            is_strict = getattr(config, "strict", True)
            validation = "strict" if is_strict else "lenient"

        # Extract column definitions
        columns: list[SchemaColumnMetadata] = []
        try:
            # Try to get schema columns using Pandera's to_schema() method
            if hasattr(gold_schema, "to_schema"):
                schema_instance = gold_schema.to_schema()
                if hasattr(schema_instance, "columns"):
                    for col_name, col_schema in schema_instance.columns.items():
                        # Get the dtype as string
                        dtype_str = (
                            str(col_schema.dtype) if col_schema.dtype else "object"
                        )
                        # Simplify dtype string (remove pandera.dtypes. prefix)
                        if "." in dtype_str:
                            dtype_str = dtype_str.split(".")[-1]

                        nullable = getattr(col_schema, "nullable", True)
                        columns.append(
                            SchemaColumnMetadata(
                                name=col_name,
                                type=dtype_str,
                                nullable=nullable,
                            )
                        )
        except Exception:
            # If schema extraction fails, leave columns empty
            pass

        return SchemaMetadata(
            contract_path=contract_path,
            version=version,
            validation=validation,
            columns=columns,
        )

    def create_gold_metadata(self, input_data: GoldMetadataInput) -> GoldMetadata:
        """Create Gold layer metadata.

        Args:
            input_data: Gold-specific metadata inputs.

        Returns:
            Complete GoldMetadata for sidecar file.
        """
        if not input_data.records:
            raise ValueError("Cannot create Gold metadata without records")

        # Build lineage from Silver refs (REQ-LINEAGE-002: Silver → Gold tracking)
        source_tables: dict[str, int] = {}
        if input_data.silver_refs:
            source_tables = {
                ref.table_name: ref.delta_version for ref in input_data.silver_refs
            }

        # Get transform info: prioritize input_data, fallback to RunContext
        transform_version = (
            input_data.transform_version
            if input_data.transform_version is not None
            else self._context.transform_version
        )
        transform_steps = list(
            input_data.transform_steps
            if input_data.transform_steps is not None
            else self._context.transform_steps
        )

        lineage = LineageMetadata(
            source_tables=source_tables,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

        # Build DQ summary (basic metrics)
        rec_count = len(input_data.records)
        dq_summary = DQSummary(
            total_records=rec_count,
            valid_records=rec_count,
        )

        # Build unified output metadata (ADR-029)
        output = BaseOutputMetadata(
            record_count=rec_count,
            total_bytes=getattr(input_data, "total_bytes", 0),
            write_started_at=getattr(input_data, "started_at", None),
            write_completed_at=input_data.completed_at,
        )

        # Build Gold-specific output extension
        output_ext = GoldOutputExt(
            partition_count=getattr(input_data, "partition_count", 0),
        )

        # Build SCD metadata if applicable
        scd = None
        if input_data.mode == GoldWriteMode.SCD2 and input_data.scd_config:
            scd = SCDMetadata(
                enabled=True,
                effective_date_column=input_data.scd_config.get(
                    "valid_from_col", "_valid_from"
                ),
                end_date_column=input_data.scd_config.get("valid_to_col", "_valid_to"),
                current_flag_column=input_data.scd_config.get(
                    "current_flag_col", "_is_current"
                ),
            )

        # Extract schema metadata from Gold schema (contract_path, version, columns)
        schema_info = self._extract_schema_metadata(input_data.gold_schema)

        # Note: schema_info uses Field(alias="schema") with populate_by_name=True
        # mypy doesn't understand this Pydantic feature, but it works at runtime
        return GoldMetadata(  # type: ignore[call-arg]
            runtime=self._build_runtime_metadata(
                completed_at=input_data.completed_at,
            ),
            pipeline=self._build_pipeline_metadata(),
            lineage=lineage,
            schema_info=schema_info,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            scd=scd,
            environment=self._get_environment_metadata(),
            governance=input_data.governance,
        )

    @classmethod
    def reset_environment_cache(cls) -> None:
        """Reset the environment metadata cache (useful for testing)."""
        cls._cached_environment = None

================================================================================
File: versioning.py
Path: services\versioning.py
================================================================================
"""Versioning and reproducibility utilities for pipeline metadata.

Provides functions to compute:
- Git commit hash for reproducibility tracking
- Config hash for change detection
- Pipeline version from config or package

These utilities support PipelineMetadata population as per RULES.md §2.3.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from functools import lru_cache
from importlib.metadata import version as pkg_version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "compute_config_hash",
    "get_git_commit",
    "get_pipeline_version",
]


@lru_cache(maxsize=1)
def get_git_commit() -> str | None:
    """Get the current git commit hash.

    Returns the short (7-character) git commit hash of HEAD.
    Returns None if:
    - Not in a git repository
    - Git is not installed
    - Any other git error occurs

    Results are cached for the process lifetime since the commit
    doesn't change during execution.

    Returns:
        Short git commit hash (e.g., 'abc1234') or None.

    Example:
        >>> commit = get_git_commit()
        >>> commit  # 'abc1234' or None
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _normalize_for_hash(obj: Any) -> Any:
    """Normalize object for deterministic hashing.

    Converts:
    - Lists to sorted lists (for sets represented as lists)
    - Dicts to sorted key-value pairs
    - None to null string
    - Other values as-is

    Args:
        obj: Object to normalize.

    Returns:
        Normalized object suitable for deterministic JSON serialization.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _normalize_for_hash(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_normalize_for_hash(item) for item in obj]
    if isinstance(obj, tuple):
        return [_normalize_for_hash(item) for item in obj]
    return obj


def compute_config_hash(config: PipelineYamlConfig | dict[str, Any]) -> str:
    """Compute SHA256 hash of pipeline configuration.

    Creates a deterministic hash of the configuration for change detection.
    The hash is computed from a normalized JSON representation to ensure
    consistency regardless of dict ordering or whitespace.

    Args:
        config: Pipeline configuration (PipelineYamlConfig or dict).

    Returns:
        SHA256 hash string (64 characters).

    Example:
        >>> config = load_pipeline_config("chembl_activity")
        >>> hash_value = compute_config_hash(config)
        >>> hash_value  # '3a7bd3e2...'
    """
    # Convert Pydantic model to dict if needed
    if hasattr(config, "model_dump"):
        config_dict = config.model_dump(mode="json", exclude_none=True)
    elif hasattr(config, "dict"):
        # Legacy Pydantic v1 support
        config_dict = config.dict(exclude_none=True)
    else:
        config_dict = dict(config)

    # Normalize for deterministic serialization
    normalized = _normalize_for_hash(config_dict)

    # Serialize to JSON with sorted keys and no whitespace
    json_str = json.dumps(normalized, sort_keys=True, separators=(",", ":"))

    # Compute SHA256 hash
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def get_pipeline_version(
    config: PipelineYamlConfig | dict[str, Any] | None = None,
) -> str:
    """Get pipeline version from config or fallback to package version.

    Priority:
    1. config.version if available
    2. bioetl package version
    3. "unknown" as last resort

    Args:
        config: Optional pipeline configuration.

    Returns:
        Version string (e.g., '1.0.0' or package version).

    Example:
        >>> version = get_pipeline_version(config)
        >>> version  # '1.0.0'
    """
    # Try to get version from config
    if config is not None:
        # Handle Pydantic model
        if hasattr(config, "version") and config.version:
            return str(config.version)
        # Handle dict
        if isinstance(config, dict) and config.get("version"):
            return str(config["version"])

    # Fallback to bioetl package version
    try:
        return pkg_version("bioetl")
    except Exception:
        return "unknown"

================================================================================
File: types.py
Path: types.py
================================================================================
"""Public types for composition layer.

This module provides type definitions and re-exports for external annotation needs.
Use these types when you need to annotate variables or function parameters
that work with composition-layer constructs.

For actual runtime imports, use the specific modules:
- ObservabilityBundle: from bioetl.composition.observability
- StorageAdapter: from bioetl.composition.factories.storage_factory
- PipelineRegistry: from bioetl.composition.registry
- get_default_registry: from bioetl.composition.registry (default instance)
- create_registry: from bioetl.composition.registry (isolated instance for tests)

Typed contexts for bootstrap functions (replacing untyped tuples):
- PipelineCallbacksContext: transform, gold_filter, gold_transform callbacks
- DQConfigsContext: Bronze/Silver/Gold DQ report configurations
- DQOutputPathsContext: DQ report output paths and flat_structure flag
- RateLimitConfig: rate and capacity for token bucket
- CircuitBreakerConfig: failure_threshold and recovery_timeout
"""

from __future__ import annotations

from bioetl.composition.bootstrap_contexts import (
    CircuitBreakerConfig,
    DQConfigsContext,
    DQOutputPathsContext,
    PipelineCallbacksContext,
    RateLimitConfig,
)
from bioetl.composition.factories.storage import StorageAdapter
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.registry import (
    PipelineDefinition,
    PipelineRegistry,
    create_registry,
    get_default_registry,
)

__all__ = [
    "CircuitBreakerConfig",
    "DQConfigsContext",
    "DQOutputPathsContext",
    "ObservabilityBundle",
    "PipelineCallbacksContext",
    "PipelineDefinition",
    "PipelineRegistry",
    "RateLimitConfig",
    "StorageAdapter",
    "create_registry",
    "get_default_registry",
]

