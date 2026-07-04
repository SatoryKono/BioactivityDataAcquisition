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
install_cached_public_exports(
    module_globals=globals(),
    public_exports=_PUBLIC_EXPORTS,
    module_name=__name__,
)
