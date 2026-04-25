"""Public resource-management composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

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
    from collections.abc import Awaitable, Callable

    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.composition._pipeline_execution import ArchiveOptions as _ArchiveOptions
    from bioetl.composition._pipeline_execution import VacuumOptions as _VacuumOptions
    from bioetl.composition._resource_management import CleanupPreviewProtocol
    from bioetl.composition._resource_management import (
        QuarantineManagerProtocol,
    )
    from bioetl.domain.types import JsonDict

ArchiveOptions: "type[_ArchiveOptions]"
VacuumOptions: "type[_VacuumOptions]"
archive_table: "Callable[[str, _ArchiveOptions], Awaitable[int]]"
get_checkpoint_manager: "Callable[[str], CheckpointManagerService]"
get_lifecycle_service: "Callable[[], MedallionLifecycleService]"
get_quarantine_manager: "Callable[[str], QuarantineManagerProtocol]"
inspect_quarantine: "Callable[[str, int], Awaitable[list[JsonDict]]]"
list_checkpoints: "Callable[[str], Awaitable[list[object]]]"
preview_cleanup: "Callable[[str], Awaitable[CleanupPreviewProtocol]]"
vacuum_table: "Callable[[str, _VacuumOptions], Awaitable[int]]"


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
