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

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.application.services.bronze_cleanup_service import (
        BronzeCleanupResult,
        BronzeCleanupService,
    )
    from bioetl.application.services.contract_migration_service import (
        ContractMigrationService,
    )
    from bioetl.application.services.vacuum_service import VacuumService
    from bioetl.composition._pipeline_execution import ArchiveOptions, VacuumOptions
    from bioetl.composition._resource_management import (
        CleanupPreviewProtocol,
        MedallionLifecycleServiceProtocol,
    )

cleanup_bronze: Callable[[int, bool], Awaitable[BronzeCleanupResult]]
get_bronze_cleanup_service: Callable[[], BronzeCleanupService]
get_contract_migration_service: Callable[[], ContractMigrationService]
get_vacuum_service: Callable[[], VacuumService]


async def archive_table(table: str, options: ArchiveOptions) -> int:
    """Retained maintenance wrapper outside ``__all__``."""
    from bioetl.composition.resources_api import archive_table as _archive_table

    return await _archive_table(table, options)


def get_lifecycle_service() -> MedallionLifecycleServiceProtocol:
    """Retained maintenance wrapper outside ``__all__``."""
    from bioetl.composition.resources_api import (
        get_lifecycle_service as _get_lifecycle_service,
    )

    return _get_lifecycle_service()


async def preview_cleanup(pipeline: str) -> CleanupPreviewProtocol:
    """Retained maintenance wrapper outside ``__all__``."""
    from bioetl.composition.resources_api import preview_cleanup as _preview_cleanup

    return await _preview_cleanup(pipeline)


async def vacuum_table(table: str, options: VacuumOptions) -> int:
    """Retained maintenance wrapper outside ``__all__``."""
    from bioetl.composition.resources_api import vacuum_table as _vacuum_table

    return await _vacuum_table(table, options)


_PUBLIC_EXPORTS = {
    "cleanup_bronze": _SERVICES_MODULE,
    "get_bronze_cleanup_service": _SERVICES_MODULE,
    "get_contract_migration_service": _SERVICES_MODULE,
    "get_vacuum_service": _SERVICES_MODULE,
}
install_cached_public_exports(
    module_globals=globals(),
    public_exports=_PUBLIC_EXPORTS,
    module_name=__name__,
)
