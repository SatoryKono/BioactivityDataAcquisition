"""Public maintenance-oriented composition API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition._lazy_exports import install_cached_public_exports

__all__ = [
    "archive_table",
    "cleanup_bronze",
    "get_bronze_cleanup_service",
    "get_contract_migration_service",
    "get_lifecycle_service",
    "get_vacuum_service",
    "preview_cleanup",
    "vacuum_table",
]

_SERVICES_MODULE = "bioetl.composition._services"
_RESOURCE_MANAGEMENT_MODULE = "bioetl.composition._resource_management"

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.application.services.bronze_cleanup_service import (
        BronzeCleanupResult,
        BronzeCleanupService,
    )
    from bioetl.application.services.contract_migration_service import (
        ContractMigrationService,
    )
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.application.services.vacuum_service import VacuumService
    from bioetl.composition._pipeline_execution import ArchiveOptions, VacuumOptions
    from bioetl.composition._resource_management import CleanupPreviewProtocol

archive_table: Callable[[str, ArchiveOptions], Awaitable[int]]
cleanup_bronze: Callable[[int, bool], Awaitable[BronzeCleanupResult]]
get_lifecycle_service: Callable[[], MedallionLifecycleService]
get_bronze_cleanup_service: Callable[[], BronzeCleanupService]
get_contract_migration_service: Callable[[], ContractMigrationService]
get_vacuum_service: Callable[[], VacuumService]
preview_cleanup: Callable[[str], Awaitable[CleanupPreviewProtocol]]
vacuum_table: Callable[[str, VacuumOptions], Awaitable[int]]

_PUBLIC_EXPORTS = {
    "archive_table": _RESOURCE_MANAGEMENT_MODULE,
    "cleanup_bronze": _SERVICES_MODULE,
    "get_bronze_cleanup_service": _SERVICES_MODULE,
    "get_contract_migration_service": _SERVICES_MODULE,
    "get_lifecycle_service": _RESOURCE_MANAGEMENT_MODULE,
    "get_vacuum_service": _SERVICES_MODULE,
    "preview_cleanup": _RESOURCE_MANAGEMENT_MODULE,
    "vacuum_table": _RESOURCE_MANAGEMENT_MODULE,
}
install_cached_public_exports(
    module_globals=globals(),
    public_exports=_PUBLIC_EXPORTS,
    module_name=__name__,
)
