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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.bootstrap.cli.health import (
        HealthServerDependencies,
        bootstrap_health_server_dependencies,
        bootstrap_health_service,
    )


_CLI_EXPORT_MODULES = {
    "HealthServerDependencies": "bioetl.composition.bootstrap.cli.health",
    "bootstrap_adr_service": "bioetl.composition.bootstrap.cli.adr",
    "bootstrap_audit_inspection_service": "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_bronze_cleanup_service": "bioetl.composition.bootstrap.cli.storage",
    "bootstrap_checkpoint_manager": "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_checkpoint_service": "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_cleanup_service": "bioetl.composition.bootstrap.cli.storage",
    "bootstrap_config_service": "bioetl.composition.bootstrap.cli.config",
    "bootstrap_contract_migration_service": "bioetl.composition.bootstrap.cli.storage",
    "bootstrap_export_service": "bioetl.composition.bootstrap.cli.storage",
    "bootstrap_health_server_dependencies": "bioetl.composition.bootstrap.cli.health",
    "bootstrap_health_service": "bioetl.composition.bootstrap.cli.health",
    "bootstrap_lifecycle_service": "bioetl.composition.bootstrap.cli.storage",
    "bootstrap_lineage_service": "bioetl.composition.bootstrap.cli.lineage",
    "bootstrap_lock_service": "bioetl.composition.bootstrap.cli.lock",
    "bootstrap_metrics_service": "bioetl.composition.bootstrap.cli.metrics",
    "bootstrap_observability_workflow_service": "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_quarantine_manager": "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_quarantine_service": "bioetl.composition.bootstrap.cli.checkpoint",
    "bootstrap_run_manifest_service": "bioetl.composition.bootstrap.cli.run_manifest",
    "bootstrap_vacuum_service": "bioetl.composition.bootstrap.cli.storage",
    "create_noop_logger": "bioetl.composition.bootstrap.cli.noop",
    "create_noop_metrics": "bioetl.composition.bootstrap.cli.noop",
    "create_noop_observability_bundle": "bioetl.composition.bootstrap.cli.noop",
    "create_noop_tracing": "bioetl.composition.bootstrap.cli.noop",
}


def __getattr__(name: str) -> object:
    """Load CLI bootstrap helpers on demand to avoid package import cycles."""
    module_name = _CLI_EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = __import__(module_name, fromlist=[name])
    return getattr(module, name)

__all__ = [
    "HealthServerDependencies",
    "bootstrap_adr_service",
    "bootstrap_audit_inspection_service",
    "bootstrap_bronze_cleanup_service",
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_cleanup_service",
    "bootstrap_config_service",
    "bootstrap_contract_migration_service",
    "bootstrap_export_service",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
    "bootstrap_lifecycle_service",
    "bootstrap_lineage_service",
    "bootstrap_lock_service",
    "bootstrap_metrics_service",
    "bootstrap_observability_workflow_service",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_service",
    "bootstrap_run_manifest_service",
    "bootstrap_vacuum_service",
    "create_noop_logger",
    "create_noop_metrics",
    "create_noop_observability_bundle",
    "create_noop_tracing",
]
