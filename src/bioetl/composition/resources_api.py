"""Public resource-management composition API."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "ArchiveOptions",
    "VacuumOptions",
    "archive_table",
    "get_checkpoint_manager",
    "get_lifecycle_service",
    "get_quarantine_manager",
    "inspect_quarantine",
    "list_checkpoints",
    "preview_cleanup",
    "vacuum_table",
]

_RESOURCE_MANAGEMENT_MODULE = "bioetl.composition._resource_management"
_PIPELINE_EXECUTION_MODULE = "bioetl.composition._pipeline_execution"
_PUBLIC_EXPORTS = {
    "ArchiveOptions": _PIPELINE_EXECUTION_MODULE,
    "VacuumOptions": _PIPELINE_EXECUTION_MODULE,
    "archive_table": _RESOURCE_MANAGEMENT_MODULE,
    "get_checkpoint_manager": _RESOURCE_MANAGEMENT_MODULE,
    "get_lifecycle_service": _RESOURCE_MANAGEMENT_MODULE,
    "get_quarantine_manager": _RESOURCE_MANAGEMENT_MODULE,
    "inspect_quarantine": _RESOURCE_MANAGEMENT_MODULE,
    "list_checkpoints": _RESOURCE_MANAGEMENT_MODULE,
    "preview_cleanup": _RESOURCE_MANAGEMENT_MODULE,
    "vacuum_table": _RESOURCE_MANAGEMENT_MODULE,
}

ArchiveOptions: object
VacuumOptions: object
archive_table: object
get_checkpoint_manager: object
get_lifecycle_service: object
get_quarantine_manager: object
inspect_quarantine: object
list_checkpoints: object
preview_cleanup: object
vacuum_table: object


def __getattr__(name: str) -> object:
    """Resolve resource-management exports lazily to keep CLI help lightweight."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
