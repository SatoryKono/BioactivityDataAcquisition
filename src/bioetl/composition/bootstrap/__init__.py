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
    # Deprecated aliases
    bootstrap_checkpoint,
    # Canonical names
    bootstrap_checkpoint_port,
    bootstrap_quarantine,
    bootstrap_quarantine_port,
    bootstrap_storage,
    bootstrap_storage_adapter,
)

# =============================================================================
# CLI-specific services (NoOp observability, admin operations)
# =============================================================================
from bioetl.composition.bootstrap.cli import (
    HealthServerDependencies,
    bootstrap_bronze_cleanup_service,
    bootstrap_checkpoint_manager,
    bootstrap_checkpoint_service,
    # Deprecated alias
    bootstrap_cleanup,
    # Canonical name
    bootstrap_cleanup_service,
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
    # Deprecated aliases
    bootstrap_composite_pipeline,
    # Canonical names
    bootstrap_composite_runner,
    bootstrap_dq_monitor,
    bootstrap_dq_monitor_port,
    bootstrap_logger,
    bootstrap_logger_port,
    bootstrap_metrics,
    bootstrap_metrics_port,
    bootstrap_observability,
    bootstrap_observability_bundle,
    bootstrap_pipeline,
    bootstrap_pipeline_runner,
    bootstrap_pipeline_runner_service,
    bootstrap_tracer,
    bootstrap_tracer_port,
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
    # Assembly (deprecated aliases)
    "bootstrap_checkpoint",
    # Checkpoint & Quarantine managers/services
    "bootstrap_checkpoint_manager",
    # Assembly (canonical)
    "bootstrap_checkpoint_port",
    "bootstrap_checkpoint_service",
    # CLI cleanup (deprecated alias)
    "bootstrap_cleanup",
    # CLI cleanup (canonical)
    "bootstrap_cleanup_service",
    # Runtime composite (deprecated alias)
    "bootstrap_composite_pipeline",
    # Runtime composite (canonical)
    "bootstrap_composite_runner",
    "bootstrap_config_service",
    # Runtime observability (deprecated aliases)
    "bootstrap_dq_monitor",
    # Runtime observability (canonical)
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
    # Runtime pipeline (deprecated alias)
    "bootstrap_pipeline",
    # Runtime pipeline (canonical)
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
    "load_composite_config",
    # Config loader
    "load_pipeline_config",
    "start_metrics_server",
    "validate_observability_preflight",
]
