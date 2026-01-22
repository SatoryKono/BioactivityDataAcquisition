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
    bootstrap_checkpoint,
    bootstrap_quarantine,
    bootstrap_storage,
)

# =============================================================================
# CLI-specific services (NoOp observability, admin operations)
# =============================================================================
from bioetl.composition.bootstrap.cli import (
    HealthServerDependencies,
    bootstrap_bronze_cleanup_service,
    bootstrap_checkpoint_manager,
    bootstrap_checkpoint_service,
    bootstrap_cleanup,
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
    bootstrap_composite_pipeline,
    bootstrap_dq_monitor,
    bootstrap_logger,
    bootstrap_metrics,
    bootstrap_observability,
    bootstrap_pipeline,
    bootstrap_pipeline_runner_service,
    bootstrap_tracer,
    load_composite_config,
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
    "bootstrap_bronze_cleanup_service",
    # Assembly (shared)
    "bootstrap_checkpoint",
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_cleanup",
    "bootstrap_composite_pipeline",
    "bootstrap_config_service",
    "bootstrap_dq_monitor",
    "bootstrap_export_service",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
    "bootstrap_lifecycle_service",
    "bootstrap_lock_service",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_metrics_service",
    "bootstrap_observability",
    "bootstrap_pipeline",
    "bootstrap_pipeline_runner_service",
    "bootstrap_quarantine",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_service",
    "bootstrap_storage",
    "bootstrap_tracer",
    "bootstrap_vacuum_service",
    "load_composite_config",
    # Config loader
    "load_pipeline_config",
    "start_metrics_server",
    "validate_observability_preflight",
]
