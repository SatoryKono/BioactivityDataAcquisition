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
    bootstrap_quarantine_port,
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
    return bootstrap_quarantine_port()
