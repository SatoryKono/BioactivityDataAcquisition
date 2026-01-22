"""Bootstrap submodule for BioETL Composition Root.

DEPRECATED: This module is maintained for backward compatibility.
New code should import from composition/bootstrap/ package instead:

- Assembly (shared): composition.bootstrap.assembly
- CLI services: composition.bootstrap.cli
- Runtime services: composition.bootstrap.runtime

All functions are re-exported from the new package structure.
"""

from __future__ import annotations

# Re-export everything from the new bootstrap package for backward compatibility
from bioetl.composition.bootstrap import (
    HealthServerDependencies,
    MetricsServerError,
    bootstrap_bronze_cleanup_service,
    # Deprecated aliases (backward compatibility)
    bootstrap_checkpoint,
    bootstrap_checkpoint_manager,
    # Canonical names (use these)
    bootstrap_checkpoint_port,
    bootstrap_checkpoint_service,
    bootstrap_cleanup,
    bootstrap_cleanup_service,
    bootstrap_composite_pipeline,
    bootstrap_composite_runner,
    bootstrap_config_service,
    bootstrap_dq_monitor,
    bootstrap_dq_monitor_port,
    bootstrap_export_service,
    bootstrap_health_server_dependencies,
    bootstrap_health_service,
    bootstrap_lifecycle_service,
    bootstrap_lock_service,
    bootstrap_logger,
    bootstrap_logger_port,
    bootstrap_metrics,
    bootstrap_metrics_port,
    bootstrap_metrics_service,
    bootstrap_observability,
    bootstrap_observability_bundle,
    bootstrap_pipeline,
    bootstrap_pipeline_runner,
    bootstrap_pipeline_runner_service,
    bootstrap_quarantine,
    bootstrap_quarantine_manager,
    bootstrap_quarantine_port,
    bootstrap_quarantine_service,
    bootstrap_storage,
    bootstrap_storage_adapter,
    bootstrap_tracer,
    bootstrap_tracer_port,
    bootstrap_vacuum_service,
    start_metrics_server,
    validate_observability_preflight,
)

__all__ = [
    "HealthServerDependencies",
    "MetricsServerError",
    "bootstrap_bronze_cleanup_service",
    # Deprecated aliases (backward compatibility)
    "bootstrap_checkpoint",
    "bootstrap_checkpoint_manager",
    # Canonical names (use these)
    "bootstrap_checkpoint_port",
    "bootstrap_checkpoint_service",
    "bootstrap_cleanup",
    "bootstrap_cleanup_service",
    "bootstrap_composite_pipeline",
    "bootstrap_composite_runner",
    "bootstrap_config_service",
    "bootstrap_dq_monitor",
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
    "bootstrap_pipeline",
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
    "start_metrics_server",
    "validate_observability_preflight",
]
