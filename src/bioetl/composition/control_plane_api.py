"""Public control-plane composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.audit_inspection_service import (
        AuditInspectionService,
    )
    from bioetl.application.services.config_service import ConfigService
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.export_service import ExportService
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.lock_service import LockService

    def get_adr_service() -> AuditInspectionService: ...

    def get_config_service() -> ConfigService: ...

    def get_export_service() -> ExportService: ...

    def get_lineage_service() -> LineageInspectionService: ...

    def get_lock_service() -> LockService: ...

    def get_run_manifest_service() -> RunManifestInspectionService: ...


__all__ = [
    "get_adr_service",
    "get_config_service",
    "get_export_service",
    "get_lineage_service",
    "get_lock_service",
    "get_run_manifest_service",
]

_SERVICES_MODULE = "bioetl.composition._services"


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
