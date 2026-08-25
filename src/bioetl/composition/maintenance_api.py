"""Public maintenance-oriented composition API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.lazy_exports import install_cached_public_exports

__all__ = [
    "cleanup_bronze",
    "get_bronze_cleanup_service",
    "get_contract_migration_service",
    "get_vacuum_service",
]

_SERVICES_MODULE = "bioetl.composition._services"
_RESOURCES_RUNTIME_MODULE = "bioetl.composition.resources_runtime"

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.application.services.ops.bronze_cleanup_service import (
        BronzeCleanupResult,
        BronzeCleanupService,
    )
    from bioetl.application.services.contracts.contract_migration_service import (
        ContractMigrationService,
    )
    from bioetl.application.services.ops.vacuum_service import VacuumService
    from bioetl.composition._pipeline_execution import ArchiveOptions, VacuumOptions
    from bioetl.composition._resource_management import (
        CleanupPreviewProtocol,
        MedallionLifecycleServiceProtocol,
    )

    async def archive_table(table: str, options: ArchiveOptions) -> int: ...

    def get_lifecycle_service() -> MedallionLifecycleServiceProtocol: ...

    async def preview_cleanup(pipeline: str) -> CleanupPreviewProtocol: ...

    async def vacuum_table(table: str, options: VacuumOptions) -> int: ...

cleanup_bronze: Callable[[int, bool], Awaitable[BronzeCleanupResult]]
get_bronze_cleanup_service: Callable[[], BronzeCleanupService]
get_contract_migration_service: Callable[[], ContractMigrationService]
get_vacuum_service: Callable[[], VacuumService]


_PUBLIC_EXPORTS = {
    "cleanup_bronze": _SERVICES_MODULE,
    "get_bronze_cleanup_service": _SERVICES_MODULE,
    "get_contract_migration_service": _SERVICES_MODULE,
    "get_vacuum_service": _SERVICES_MODULE,
}
_COMPATIBILITY_EXPORTS = {
    "archive_table": _RESOURCES_RUNTIME_MODULE,
    "get_lifecycle_service": _RESOURCES_RUNTIME_MODULE,
    "preview_cleanup": _RESOURCES_RUNTIME_MODULE,
    "vacuum_table": _RESOURCES_RUNTIME_MODULE,
}
_LAZY_EXPORTS = {**_PUBLIC_EXPORTS, **_COMPATIBILITY_EXPORTS}
install_cached_public_exports(
    module_globals=globals(),
    public_exports=_LAZY_EXPORTS,
    module_name=__name__,
)
