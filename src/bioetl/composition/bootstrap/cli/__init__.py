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

from bioetl.composition.bootstrap.cli.adr import bootstrap_adr_service
from bioetl.composition.bootstrap.cli.checkpoint import (
    bootstrap_audit_inspection_service,
    bootstrap_checkpoint_manager,
    bootstrap_checkpoint_service,
    bootstrap_observability_workflow_service,
    bootstrap_quarantine_manager,
    bootstrap_quarantine_service,
)
from bioetl.composition.bootstrap.cli.config import bootstrap_config_service
from bioetl.composition.bootstrap.cli.health import (
    HealthServerDependencies,
    bootstrap_health_server_dependencies,
    bootstrap_health_service,
)
from bioetl.composition.bootstrap.cli.lineage import bootstrap_lineage_service
from bioetl.composition.bootstrap.cli.lock import bootstrap_lock_service
from bioetl.composition.bootstrap.cli.metrics import bootstrap_metrics_service
from bioetl.composition.bootstrap.cli.noop import (
    create_noop_logger,
    create_noop_metrics,
    create_noop_observability_bundle,
    create_noop_tracing,
)
from bioetl.composition.bootstrap.cli.run_manifest import (
    bootstrap_run_manifest_service,
)
from bioetl.composition.bootstrap.cli.storage import (
    bootstrap_bronze_cleanup_service,
    bootstrap_cleanup_service,
    bootstrap_contract_migration_service,
    bootstrap_export_service,
    bootstrap_lifecycle_service,
    bootstrap_vacuum_service,
)

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
