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

Public names are resolved lazily so light-weight imports, such as test fixtures
that only need a helper submodule, do not pay the cost of importing the entire
runtime bootstrap tree.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "HealthServerDependencies",
    "bootstrap_adr_service",
    "bootstrap_audit_inspection_service",
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
    "bootstrap_observability_workflow_service",
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

_PUBLIC_EXPORTS: dict[str, str] = {
    "HealthServerDependencies": "bioetl.composition.bootstrap.cli",
    "bootstrap_adr_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_audit_inspection_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_bronze_cleanup_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_checkpoint_manager": "bioetl.composition.bootstrap.cli",
    "bootstrap_checkpoint_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_cleanup_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_composite_checkpoint_port": "bioetl.composition.bootstrap.assembly",
    "bootstrap_composite_runner": "bioetl.composition.bootstrap.runtime",
    "bootstrap_config_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_contract_migration_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_export_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_health_server_dependencies": "bioetl.composition.bootstrap.cli",
    "bootstrap_health_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_lifecycle_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_lineage_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_lock_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_logger_port": "bioetl.composition.bootstrap.runtime",
    "bootstrap_metrics_port": "bioetl.composition.bootstrap.runtime",
    "bootstrap_metrics_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_observability_workflow_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_pipeline_runner": "bioetl.composition.bootstrap.runtime",
    "bootstrap_pipeline_runner_service": "bioetl.composition.bootstrap.runtime",
    "bootstrap_quarantine_manager": "bioetl.composition.bootstrap.cli",
    "bootstrap_quarantine_port": "bioetl.composition.bootstrap.assembly",
    "bootstrap_quarantine_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_run_manifest_service": "bioetl.composition.bootstrap.cli",
    "bootstrap_vacuum_service": "bioetl.composition.bootstrap.cli",
    "load_composite_config": "bioetl.composition.bootstrap.runtime",
    "load_pipeline_config": "bioetl.infrastructure.config.pipeline_config_api",
    "maybe_start_metrics_server": "bioetl.composition.bootstrap.runtime",
}


def __getattr__(name: str) -> Any:  # Any: lazy re-export preserves the original symbol type at lookup time.
    """Resolve bootstrap re-exports lazily to avoid eager runtime imports."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from bioetl.infrastructure.compat.pandera_compat import (
        apply_pandera_typing_compat_if_needed,
    )

    apply_pandera_typing_compat_if_needed()
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
