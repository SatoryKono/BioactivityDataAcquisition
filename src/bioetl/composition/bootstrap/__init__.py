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

Internal bootstrap helpers (observability primitives, assembly pure functions,
deprecated aliases) should be imported directly from submodules:
- ``bioetl.composition.bootstrap.assembly``
- ``bioetl.composition.bootstrap.runtime``
"""

from __future__ import annotations

# =============================================================================
# Assembly (shared infrastructure without side-effects)
# =============================================================================
from bioetl.composition.bootstrap.assembly import (
    bootstrap_composite_checkpoint_port,
    bootstrap_quarantine_port,
)

# =============================================================================
# CLI-specific services (NoOp observability, admin operations)
# =============================================================================
from bioetl.composition.bootstrap.cli import (
    HealthServerDependencies,
    bootstrap_adr_service,
    bootstrap_bronze_cleanup_service,
    bootstrap_checkpoint_manager,
    bootstrap_checkpoint_service,
    bootstrap_cleanup_service,
    bootstrap_config_service,
    bootstrap_contract_migration_service,
    bootstrap_export_service,
    bootstrap_health_server_dependencies,
    bootstrap_health_service,
    bootstrap_lifecycle_service,
    bootstrap_lineage_service,
    bootstrap_lock_service,
    bootstrap_metrics_service,
    bootstrap_quarantine_manager,
    bootstrap_quarantine_service,
    bootstrap_run_manifest_service,
    bootstrap_vacuum_service,
)

# =============================================================================
# Runtime services (full observability, pipeline execution)
# =============================================================================
from bioetl.composition.bootstrap.runtime import (
    bootstrap_composite_runner,
    bootstrap_logger_port,
    bootstrap_metrics_port,
    bootstrap_pipeline_runner,
    bootstrap_pipeline_runner_service,
    load_composite_config,
    maybe_start_metrics_server,
)

# =============================================================================
# Config loader (re-exported for convenience)
# =============================================================================
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

__all__ = [
    "HealthServerDependencies",
    "bootstrap_adr_service",
    "bootstrap_bronze_cleanup_service",
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_cleanup_service",
    "bootstrap_composite_checkpoint_port",
    "bootstrap_composite_runner",
    "bootstrap_config_service",
    "bootstrap_contract_migration_service",
    "bootstrap_export_service",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
    "bootstrap_lifecycle_service",
    "bootstrap_lineage_service",
    "bootstrap_lock_service",
    "bootstrap_logger_port",
    "bootstrap_metrics_port",
    "bootstrap_metrics_service",
    "bootstrap_pipeline_runner",
    "bootstrap_pipeline_runner_service",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_port",
    "bootstrap_quarantine_service",
    "bootstrap_run_manifest_service",
    "bootstrap_vacuum_service",
    "load_composite_config",
    "load_pipeline_config",
    "maybe_start_metrics_server",
]
