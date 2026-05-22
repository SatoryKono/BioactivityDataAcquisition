"""Public services-oriented composition API."""

from __future__ import annotations

from bioetl.composition._services import (
    cleanup_bronze,
    get_adr_service,
    get_audit_service,
    get_bronze_cleanup_service,
    get_checkpoint_service,
    get_config_service,
    get_contract_migration_service,
    get_export_service,
    get_forensic_run_diff_service,
    get_health_service,
    get_lineage_service,
    get_lock_service,
    get_metrics_service,
    get_observability_workflow_service,
    get_pipeline_runner_service,
    get_run_manifest_service,
    get_vacuum_service,
    get_workflow_execution_service,
    get_workflow_inspection_service,
    get_workflow_runner_service,
    load_workflow_config,
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
    "get_forensic_run_diff_service",
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
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "get_workflow_runner_service",
    "load_workflow_config",
]


def get_health_server_dependencies():
    """Return the public health listener dependency bundle."""
    from bioetl.composition._services import (
        get_health_server_dependencies as _get_health_server_dependencies,
    )

    return _get_health_server_dependencies()


def get_quarantine_service():
    """Return the public quarantine admin service."""
    from bioetl.composition._services import (
        get_quarantine_service as _get_quarantine_service,
    )

    return _get_quarantine_service()


def get_quarantine_port():
    """Return the shared public quarantine storage port."""
    from bioetl.composition._services import (
        get_quarantine_port as _get_quarantine_port,
    )

    return _get_quarantine_port()
