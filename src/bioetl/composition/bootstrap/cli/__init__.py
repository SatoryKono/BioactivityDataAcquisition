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
- checkpoint: runtime-service and admin-service bootstrap for checkpoint operations
- config: ConfigService bootstrap
- health: HealthService and health server dependencies
- lock: LockService bootstrap
- metrics: MetricsService for server management (not metrics collection)
- storage: Maintenance services (cleanup, vacuum, export, lifecycle)
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from bioetl.infrastructure.adr.fs_adr_service import FilesystemAdrCatalog
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.control_plane import FileControlPlaneArtifactLifecycleStore
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.domain.ports import AdrServicePort
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies,
        bootstrap_health_server_dependencies,
        bootstrap_health_service,
    )
    from bioetl.infrastructure.control_plane import (
        FileControlPlaneArtifactLifecycleStore,
    )

_CLI_HEALTH_MODULE = "bioetl.composition.bootstrap.cli.health"
_CLI_CHECKPOINT_MODULE = "bioetl.composition.bootstrap.cli.checkpoint"
_CLI_STORAGE_MODULE = "bioetl.composition.bootstrap.cli.storage"
_CLI_NOOP_MODULE = "bioetl.composition.bootstrap.cli.noop"


_CLI_EXPORT_MODULES = {
    "HealthServerDependencies": _CLI_HEALTH_MODULE,
    "bootstrap_audit_inspection_service": _CLI_CHECKPOINT_MODULE,
    "bootstrap_bronze_cleanup_service": _CLI_STORAGE_MODULE,
    "bootstrap_checkpoint_runtime_service": _CLI_CHECKPOINT_MODULE,
    "bootstrap_checkpoint_service": _CLI_CHECKPOINT_MODULE,
    "bootstrap_cleanup_service": _CLI_STORAGE_MODULE,
    "bootstrap_config_service": "bioetl.composition.bootstrap.cli.config",
    "bootstrap_contract_migration_service": _CLI_STORAGE_MODULE,
    "bootstrap_export_service": _CLI_STORAGE_MODULE,
    "bootstrap_forensic_run_diff_service": "bioetl.composition.bootstrap.cli.run_manifest",
    "bootstrap_health_server_dependencies": _CLI_HEALTH_MODULE,
    "bootstrap_health_service": _CLI_HEALTH_MODULE,
    "bootstrap_lifecycle_service": _CLI_STORAGE_MODULE,
    "bootstrap_lineage_service": "bioetl.composition.bootstrap.cli.lineage",
    "bootstrap_lock_service": "bioetl.composition.bootstrap.cli.lock",
    "bootstrap_metrics_service": "bioetl.composition.bootstrap.cli.metrics",
    "bootstrap_observability_workflow_service": _CLI_CHECKPOINT_MODULE,
    "bootstrap_quarantine_runtime_service": _CLI_CHECKPOINT_MODULE,
    "bootstrap_quarantine_service": _CLI_CHECKPOINT_MODULE,
    "bootstrap_run_manifest_service": "bioetl.composition.bootstrap.cli.run_manifest",
    "bootstrap_vacuum_service": _CLI_STORAGE_MODULE,
    "create_noop_logger": _CLI_NOOP_MODULE,
    "create_noop_metrics": _CLI_NOOP_MODULE,
    "create_noop_observability_bundle": _CLI_NOOP_MODULE,
    "create_noop_tracing": _CLI_NOOP_MODULE,
}


def bootstrap_adr_service() -> AdrServicePort:
    """Bootstrap ADR service using the default filesystem-backed catalog."""
    from typing import cast

    service = FilesystemAdrCatalog()
    return cast("AdrServicePort", service)


def bootstrap_control_plane_lifecycle_store() -> FileControlPlaneArtifactLifecycleStore:
    """Build the file-backed control-plane lifecycle store for CLI operations."""
    from pathlib import Path

    from bioetl.composition.runtime_builders.config_access import get_settings

    settings = get_settings()
    output_root = Path(settings.data_dir) / "output"
    return FileControlPlaneArtifactLifecycleStore(
        base_path=output_root / "control",
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
    )


def __getattr__(name: str) -> object:
    """Load CLI bootstrap helpers on demand to avoid package import cycles."""
    module_name = _CLI_EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    return getattr(module, name)


__all__ = [
    "HealthServerDependencies",
    "bootstrap_adr_service",
    "bootstrap_audit_inspection_service",
    "bootstrap_bronze_cleanup_service",
    "bootstrap_checkpoint_runtime_service",
    "bootstrap_checkpoint_service",
    "bootstrap_cleanup_service",
    "bootstrap_config_service",
    "bootstrap_contract_migration_service",
    "bootstrap_control_plane_lifecycle_store",
    "bootstrap_export_service",
    "bootstrap_forensic_run_diff_service",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
    "bootstrap_lifecycle_service",
    "bootstrap_lineage_service",
    "bootstrap_lock_service",
    "bootstrap_metrics_service",
    "bootstrap_observability_workflow_service",
    "bootstrap_quarantine_runtime_service",
    "bootstrap_quarantine_service",
    "bootstrap_run_manifest_service",
    "bootstrap_vacuum_service",
    "create_noop_logger",
    "create_noop_metrics",
    "create_noop_observability_bundle",
    "create_noop_tracing",
]
