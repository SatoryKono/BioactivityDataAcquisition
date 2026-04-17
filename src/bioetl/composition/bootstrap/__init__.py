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

_BOOTSTRAP_CLI_MODULE = "bioetl.composition.bootstrap.cli"
_BOOTSTRAP_ASSEMBLY_MODULE = "bioetl.composition.bootstrap.assembly"
_BOOTSTRAP_RUNTIME_MODULE = "bioetl.composition.bootstrap.runtime"

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
    "HealthServerDependencies": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_adr_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_audit_inspection_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_bronze_cleanup_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_checkpoint_manager": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_checkpoint_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_cleanup_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_composite_checkpoint_port": _BOOTSTRAP_ASSEMBLY_MODULE,
    "bootstrap_composite_runner": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_config_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_contract_migration_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_export_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_health_server_dependencies": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_health_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_lifecycle_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_lineage_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_lock_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_logger_port": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_metrics_port": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_metrics_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_observability_workflow_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_pipeline_runner": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_pipeline_runner_service": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_quarantine_manager": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_quarantine_port": _BOOTSTRAP_ASSEMBLY_MODULE,
    "bootstrap_quarantine_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_run_manifest_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_vacuum_service": _BOOTSTRAP_CLI_MODULE,
    "load_composite_config": _BOOTSTRAP_RUNTIME_MODULE,
    "load_pipeline_config": "bioetl.infrastructure.config.pipeline_config_api",
    "maybe_start_metrics_server": _BOOTSTRAP_RUNTIME_MODULE,
}

# ``importlib.reload`` preserves the existing module dict. Clear any cached lazy
# exports so post-reload attribute access still flows through ``__getattr__``.
for _cached_export_name in tuple(_PUBLIC_EXPORTS):
    globals().pop(_cached_export_name, None)


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
