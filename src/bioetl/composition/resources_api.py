"""Public resource-management composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition._pipeline_execution import ArchiveOptions, VacuumOptions
    from bioetl.composition._resource_management import (
        CheckpointManagerProtocol,
        CleanupPreviewProtocol,
        MedallionLifecycleServiceProtocol,
        QuarantineManagerProtocol,
    )
    from bioetl.domain.types import JsonDict

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

if TYPE_CHECKING:

    async def archive_table(table: str, options: ArchiveOptions) -> int: ...

    def get_checkpoint_manager(pipeline: str) -> CheckpointManagerProtocol: ...

    def get_lifecycle_service() -> MedallionLifecycleServiceProtocol: ...

    def get_quarantine_manager(pipeline: str) -> QuarantineManagerProtocol: ...

    async def inspect_quarantine(
        pipeline: str,
        limit: int = 100,
    ) -> list[JsonDict]: ...

    async def list_checkpoints(pipeline: str) -> list[object]: ...

    async def preview_cleanup(pipeline: str) -> CleanupPreviewProtocol: ...

    async def vacuum_table(table: str, options: VacuumOptions) -> int: ...


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
