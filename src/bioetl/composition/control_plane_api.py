"""Public control-plane composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
    "get_adr_service",
    "get_config_service",
    "get_export_service",
    "get_lineage_service",
    "get_lock_service",
    "get_run_manifest_service",
]

_SERVICES_MODULE = "bioetl.composition._services"

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.config_service import ConfigService
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.export_service import ExportService
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.lock_service import LockService
    from bioetl.domain.ports import AdrServicePort

get_adr_service: "Callable[[], AdrServicePort]"
get_config_service: "Callable[[], ConfigService]"
get_export_service: "Callable[[], ExportService]"
get_lineage_service: "Callable[[], LineageInspectionService]"
get_lock_service: "Callable[[], LockService]"
get_run_manifest_service: "Callable[[], RunManifestInspectionService]"


def __getattr__(name: str) -> object:
    """Resolve control-plane exports lazily to avoid CLI import fan-out."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_SERVICES_MODULE), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
