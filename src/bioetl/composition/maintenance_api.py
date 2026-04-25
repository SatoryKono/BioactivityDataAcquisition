"""Public maintenance-oriented composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

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
    from bioetl.application.services import ContractMigrationService
    from bioetl.application.services.vacuum_service import VacuumService

cleanup_bronze: "Callable[[int, bool], Awaitable[BronzeCleanupResult]]"
get_bronze_cleanup_service: "Callable[[], BronzeCleanupService]"
get_contract_migration_service: "Callable[[], ContractMigrationService]"
get_vacuum_service: "Callable[[], VacuumService]"


def __getattr__(name: str) -> object:
    """Resolve maintenance exports lazily to avoid CLI import fan-out."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_SERVICES_MODULE), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
