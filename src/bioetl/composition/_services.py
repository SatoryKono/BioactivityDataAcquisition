"""Thin composition facade for service bootstrap entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from bioetl.composition._service_bootstraps import (
    bootstrap_adr_service,
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
    resolve_bootstrap_attr,
)


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


def _ensure_registrations(registry: object | None = None) -> None:
    """Ensure providers and pipelines are registered lazily to avoid cycles."""
    from bioetl.composition._pipeline_execution import (
        _ensure_registrations as ensure_registrations_impl,
    )

    ensure_registrations_impl(registry=registry)


def get_checkpoint_service() -> object:
    """Get checkpoint administration service."""
    _ensure_registrations()
    return bootstrap_checkpoint_service()


def get_audit_service() -> object:
    """Get an audit inspection service for operator diagnostics operations."""
    _ensure_registrations()
    bootstrap = cast(Callable[[], object], resolve_bootstrap_attr("bootstrap_audit_inspection_service"))
    return bootstrap()


def get_quarantine_service() -> object:
    """Get quarantine administration service."""
    _ensure_registrations()
    return bootstrap_quarantine_service()


def get_bronze_cleanup_service() -> object:
    """Get Bronze cleanup service."""
    _ensure_registrations()
    return bootstrap_bronze_cleanup_service()


def get_vacuum_service() -> VacuumService:
    """Get batch vacuum service."""
    _ensure_registrations()
    return cast("VacuumService", bootstrap_vacuum_service())


def get_export_service() -> ExportService:
    """Get Delta export service."""
    _ensure_registrations()
    return cast("ExportService", bootstrap_export_service())


def get_lock_service() -> LockService:
    """Get administrative lock service."""
    _ensure_registrations()
    return cast("LockService", bootstrap_lock_service())


async def cleanup_bronze(
    retention_days: int = 90,
    dry_run: bool = False,
) -> BronzeCleanupResult:
    """Clean up Bronze files based on retention policy."""
    service = get_bronze_cleanup_service()
    result = await service.cleanup(
        retention_days=retention_days,
        dry_run=dry_run,
    )
    return result


def get_pipeline_runner_service(
    registry: object | None = None,
) -> object:
    """Get universal pipeline runner service."""
    _ensure_registrations(registry=registry)
    return bootstrap_pipeline_runner_service(registry=registry)


def get_config_service() -> object:
    """Get application configuration service."""
    _ensure_registrations()
    return bootstrap_config_service()


def load_workflow_config(name: str) -> object:
    """Load workflow YAML through the canonical composition service seam."""
    from bioetl.infrastructure.config.workflow_config_api import (
        load_workflow_config as load_workflow_config_impl,
    )

    return load_workflow_config_impl(name)


def get_contract_migration_service() -> object:
    """Get the contract migration planner service."""
    _ensure_registrations()
    bootstrap = cast(Callable[[], object], resolve_bootstrap_attr("bootstrap_contract_migration_service"))
    return bootstrap()


def get_run_manifest_service() -> object:
    """Get a run-manifest inspection service for control-plane operations."""
    _ensure_registrations()
    bootstrap = cast(Callable[[], object], resolve_bootstrap_attr("bootstrap_run_manifest_service"))
    return bootstrap()


def get_lineage_service() -> object:
    """Get a lineage inspection service for traceability operations."""
    _ensure_registrations()
    bootstrap = cast(Callable[[], object], resolve_bootstrap_attr("bootstrap_lineage_service"))
    return bootstrap()


def get_health_service() -> object:
    """Get provider health service."""
    _ensure_registrations()
    return bootstrap_health_service()


def get_observability_workflow_service() -> object:
    """Get workflow-level observability diagnostics helpers."""
    _ensure_registrations()
    bootstrap = cast(
        Callable[[], object],
        resolve_bootstrap_attr("bootstrap_observability_workflow_service"),
    )
    return bootstrap()


def get_health_server_dependencies() -> object:
    """Get dependencies for the health server."""
    _ensure_registrations()
    return bootstrap_health_server_dependencies()


def get_metrics_service() -> object:
    """Get metrics administration service."""
    _ensure_registrations()
    return bootstrap_metrics_service()


def get_adr_service() -> object:
    """Get ADR management port."""
    _ensure_registrations()
    return bootstrap_adr_service()


def get_quarantine_port() -> object:
    """Get the shared low-level quarantine port."""
    _ensure_registrations()
    return bootstrap_quarantine_port()
