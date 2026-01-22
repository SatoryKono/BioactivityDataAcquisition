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
from bioetl.composition.bootstrap.cli.storage import (
    bootstrap_bronze_cleanup_service,
    bootstrap_cleanup,
    bootstrap_export_service,
    bootstrap_lifecycle_service,
    bootstrap_vacuum_service,
)

__all__ = [
    # Health
    "HealthServerDependencies",
    # Storage & Maintenance
    "bootstrap_bronze_cleanup_service",
    # Checkpoint & Quarantine
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_cleanup",
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
]
