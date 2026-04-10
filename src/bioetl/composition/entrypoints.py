"""Public composition entrypoint focused on execution-oriented APIs.

`bioetl.composition.entrypoints` remains a stable import seam, but its explicit
public surface (`__all__`) is intentionally narrow and execution-focused.

Service and resource-management helpers remain available through compatibility
lookup in ``__getattr__`` and emit deprecation warnings with canonical import
targets (`services_api` / `resources_api`).
"""

from __future__ import annotations

import warnings
from importlib import import_module
from typing import Any

__all__ = [
    "ArchiveOptions",
    "PipelineRunResult",
    "RunOptions",
    "RunResult",
    "VacuumOptions",
    "bootstrap_composite_runner",
    "build_pipeline_context",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "load_composite_config",
    "load_pipeline_config",
    "maybe_start_metrics_server",
    "push_metrics_to_gateway",
    "run_pipeline",
    "start_metrics_server",
]

_PUBLIC_SYMBOL_TARGETS: dict[str, str] = {
    "ArchiveOptions": "bioetl.composition.execution_api",
    "PipelineRunResult": "bioetl.composition.execution_api",
    "RunOptions": "bioetl.composition.execution_api",
    "RunResult": "bioetl.composition.execution_api",
    "VacuumOptions": "bioetl.composition.execution_api",
    "bootstrap_composite_runner": "bioetl.composition.composite_api",
    "build_pipeline_context": "bioetl.composition.execution_api",
    "create_pipeline_runner": "bioetl.composition.execution_api",
    "ensure_metrics_server_started": "bioetl.composition.execution_api",
    "load_composite_config": "bioetl.composition.composite_api",
    "load_pipeline_config": "bioetl.composition.composite_api",
    "maybe_start_metrics_server": "bioetl.composition.execution_api",
    "push_metrics_to_gateway": "bioetl.composition.execution_api",
    "run_pipeline": "bioetl.composition.execution_api",
    "start_metrics_server": "bioetl.composition.observability_api",
}

_LEGACY_SYMBOL_TARGETS: dict[str, str] = {
    # services_api
    "cleanup_bronze": "bioetl.composition.services_api",
    "get_adr_service": "bioetl.composition.services_api",
    "get_bronze_cleanup_service": "bioetl.composition.services_api",
    "get_checkpoint_service": "bioetl.composition.services_api",
    "get_config_service": "bioetl.composition.services_api",
    "get_export_service": "bioetl.composition.services_api",
    "get_health_server_dependencies": "bioetl.composition.services_api",
    "get_health_service": "bioetl.composition.services_api",
    "get_lock_service": "bioetl.composition.services_api",
    "get_metrics_service": "bioetl.composition.services_api",
    "get_pipeline_runner_service": "bioetl.composition.services_api",
    "get_quarantine_port": "bioetl.composition.services_api",
    "get_quarantine_service": "bioetl.composition.services_api",
    "get_vacuum_service": "bioetl.composition.services_api",
    # resources_api
    "archive_table": "bioetl.composition.resources_api",
    "get_checkpoint_manager": "bioetl.composition.resources_api",
    "get_lifecycle_service": "bioetl.composition.resources_api",
    "get_quarantine_manager": "bioetl.composition.resources_api",
    "inspect_quarantine": "bioetl.composition.resources_api",
    "list_checkpoints": "bioetl.composition.resources_api",
    "preview_cleanup": "bioetl.composition.resources_api",
    "vacuum_table": "bioetl.composition.resources_api",
}


def __getattr__(name: str) -> Any:  # Any: lazy compatibility exports resolve to heterogeneous symbol types.
    """Resolve public and deprecated entrypoint symbols lazily."""
    module_name = _PUBLIC_SYMBOL_TARGETS.get(name)
    if module_name is not None:
        module = import_module(module_name)
        value = getattr(module, name)
        globals()[name] = value
        return value

    module_name = _LEGACY_SYMBOL_TARGETS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    value = getattr(module, name)
    warnings.warn(
        (
            f"`bioetl.composition.entrypoints.{name}` is deprecated; "
            f"import `{name}` from `{module_name}` instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable introspection results including legacy compatibility names."""
    return sorted(
        set(globals()) | set(__all__) | set(_PUBLIC_SYMBOL_TARGETS) | set(_LEGACY_SYMBOL_TARGETS)
    )
