"""Service factory entrypoints for CLI and other interfaces."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services import (
        BronzeCleanupResult,
        BronzeCleanupService,
        ConfigService,
        ContractMigrationService,
        ExportService,
        HealthService,
        LineageInspectionService,
        MetricsService,
        ObservabilityWorkflowService,
        PipelineRunnerService,
        QuarantineService,
        RunManifestInspectionService,
        VacuumService,
    )
    from bioetl.application.services.audit_inspection_service import (
        AuditInspectionService,
    )
    from bioetl.application.services.checkpoint_service import CheckpointService
    from bioetl.application.services.lock_service import LockService
    from bioetl.composition import PipelineRegistry
    from bioetl.composition.bootstrap import HealthServerDependencies
    from bioetl.domain.ports import AdrServicePort, QuarantinePort
    from bioetl.domain.workflow import WorkflowConfig


__all__ = [
    "cleanup_bronze",
    "get_adr_service",
    "get_audit_service",
    "get_bronze_cleanup_service",
    "get_checkpoint_service",
    "get_config_service",
    "get_contract_migration_service",
    "get_export_service",
    "get_health_server_dependencies",
    "get_health_service",
    "get_lineage_service",
    "get_lock_service",
    "get_metrics_service",
    "get_observability_workflow_service",
    "get_pipeline_runner_service",
    "get_quarantine_port",
    "get_quarantine_service",
    "get_run_manifest_service",
    "get_vacuum_service",
    "load_workflow_config",
]


def _ensure_registrations(registry: PipelineRegistry | None = None) -> None:
    """Ensure providers and pipelines are registered lazily to avoid cycles."""
    from bioetl.composition._pipeline_execution import (
        _ensure_registrations as ensure_registrations_impl,
    )

    ensure_registrations_impl(registry=registry)


def _bootstrap_attr(name: str) -> object:
    """Resolve one bootstrap export lazily to keep CLI imports light."""
    bootstrap = import_module("bioetl.composition.bootstrap")
    return getattr(bootstrap, name)


def bootstrap_checkpoint_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for checkpoint service bootstrap patch points."""
    return _bootstrap_attr("bootstrap_checkpoint_service")(*args, **kwargs)


def bootstrap_quarantine_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for quarantine service bootstrap patch points."""
    return _bootstrap_attr("bootstrap_quarantine_service")(*args, **kwargs)


def bootstrap_bronze_cleanup_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for bronze cleanup bootstrap patch points."""
    return _bootstrap_attr("bootstrap_bronze_cleanup_service")(*args, **kwargs)


def bootstrap_vacuum_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for vacuum service bootstrap patch points."""
    return _bootstrap_attr("bootstrap_vacuum_service")(*args, **kwargs)


def bootstrap_export_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for export service bootstrap patch points."""
    return _bootstrap_attr("bootstrap_export_service")(*args, **kwargs)


def bootstrap_lock_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for lock service bootstrap patch points."""
    return _bootstrap_attr("bootstrap_lock_service")(*args, **kwargs)


def bootstrap_pipeline_runner_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for pipeline runner bootstrap patch points."""
    return _bootstrap_attr("bootstrap_pipeline_runner_service")(*args, **kwargs)


def bootstrap_config_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for config service bootstrap patch points."""
    return _bootstrap_attr("bootstrap_config_service")(*args, **kwargs)


def bootstrap_health_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for health service bootstrap patch points."""
    return _bootstrap_attr("bootstrap_health_service")(*args, **kwargs)


def bootstrap_health_server_dependencies(*args: object, **kwargs: object) -> object:
    """Compatibility seam for health server dependency bootstrap patch points."""
    return _bootstrap_attr("bootstrap_health_server_dependencies")(*args, **kwargs)


def bootstrap_metrics_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for metrics service bootstrap patch points."""
    return _bootstrap_attr("bootstrap_metrics_service")(*args, **kwargs)


def bootstrap_adr_service(*args: object, **kwargs: object) -> object:
    """Compatibility seam for ADR service bootstrap patch points."""
    return _bootstrap_attr("bootstrap_adr_service")(*args, **kwargs)


def bootstrap_quarantine_port(*args: object, **kwargs: object) -> object:
    """Compatibility seam for quarantine port bootstrap patch points."""
    return _bootstrap_attr("bootstrap_quarantine_port")(*args, **kwargs)


def get_checkpoint_service() -> CheckpointService:
    """Get a checkpoint service for administrative operations.

    Used for listing, deleting, and inspecting checkpoints across all pipelines.
    This is the recommended way to manage checkpoints from CLI or other interfaces.

    Returns:
        CheckpointService instance.
    """
    _ensure_registrations()
    return bootstrap_checkpoint_service()


def get_audit_service() -> AuditInspectionService:
    """Get an audit inspection service for operator diagnostics operations."""
    _ensure_registrations()
    return _bootstrap_attr("bootstrap_audit_inspection_service")()


def get_quarantine_service() -> QuarantineService:
    """Get a quarantine service for administrative operations.

    Used for inspecting, replaying, and purging quarantine records.
    This is the recommended way to manage quarantine from CLI or other interfaces.

    Returns:
        QuarantineService instance.
    """
    _ensure_registrations()
    return bootstrap_quarantine_service()


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Get a bronze cleanup service for maintenance operations.

    Used for Bronze layer retention cleanup per RULES.md §2.1.
    This is the recommended way to manage Bronze cleanup from CLI.
    """
    _ensure_registrations()
    return bootstrap_bronze_cleanup_service()


def get_vacuum_service() -> VacuumService:
    """Get a vacuum service for batch vacuum operations.

    Used for vacuuming multiple Delta tables at once.
    This is the recommended way to vacuum tables from CLI.
    """
    _ensure_registrations()
    return bootstrap_vacuum_service()


def get_export_service() -> ExportService:
    """Get an export service for exporting Delta Lake tables.

    Used for exporting Silver/Gold Delta tables to CSV, XLSX, and TSV formats.
    This is the recommended way to export tables from CLI.
    """
    _ensure_registrations()
    return bootstrap_export_service()


def get_lock_service() -> LockService:
    """Get a lock service for administrative lock operations.

    Used for releasing stale locks and checking lock status.
    This is the recommended way to manage locks from CLI.

    Note: Uses in-memory locking which only affects the current process.
    Lock operations are local to this process instance.
    """
    _ensure_registrations()
    return bootstrap_lock_service()


async def cleanup_bronze(
    retention_days: int = 90,
    dry_run: bool = False,
) -> BronzeCleanupResult:
    """Clean up old Bronze files based on retention policy.

    Convenience function for Bronze cleanup operations.
    Removes files older than the specified retention period.
    """
    service = get_bronze_cleanup_service()
    result: BronzeCleanupResult = await service.cleanup(
        retention_days=retention_days,
        dry_run=dry_run,
    )
    return result


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
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
    _ensure_registrations(registry=registry)
    return bootstrap_pipeline_runner_service(registry=registry)


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


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load workflow YAML through the canonical composition service seam."""
    from bioetl.infrastructure.config.workflow_config_api import (
        load_workflow_config as load_workflow_config_impl,
    )

    return load_workflow_config_impl(name)


def get_contract_migration_service() -> ContractMigrationService:
    """Get the contract migration planner service."""
    _ensure_registrations()
    return _bootstrap_attr("bootstrap_contract_migration_service")()


def get_run_manifest_service() -> RunManifestInspectionService:
    """Get a run-manifest inspection service for control-plane operations."""
    _ensure_registrations()
    return _bootstrap_attr("bootstrap_run_manifest_service")()


def get_lineage_service() -> LineageInspectionService:
    """Get a lineage inspection service for traceability operations."""
    _ensure_registrations()
    return _bootstrap_attr("bootstrap_lineage_service")()


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


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Get workflow-level observability diagnostics helpers."""
    _ensure_registrations()
    return _bootstrap_attr("bootstrap_observability_workflow_service")()


def get_health_server_dependencies() -> HealthServerDependencies:
    """Get dependencies for HealthServer via composition root.

    Returns HealthServerDependencies with PrometheusMetrics and
    ProviderHealthMonitor. HealthServer is created in interfaces layer.

    Returns:
        Health server dependencies.
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


def get_adr_service() -> AdrServicePort:
    """Get ADR service (port) for ADR management operations.

    Provides read-only access to ADR documents and validation.

    Returns:
        AdrServicePort instance.
    """
    _ensure_registrations()
    return bootstrap_adr_service()


def get_quarantine_port() -> QuarantinePort:
    """Get the shared quarantine port for direct quarantine operations.

    This provides direct access to the QuarantinePort for low-level
    quarantine operations. For most use cases, prefer get_quarantine_service()
    which provides a higher-level interface.

    Returns:
        QuarantinePort instance for quarantine operations.

    Example:
        >>> port = get_quarantine_port()
        >>> records = await port.inspect("chembl_activity", limit=10)
    """
    _ensure_registrations()
    return bootstrap_quarantine_port()
