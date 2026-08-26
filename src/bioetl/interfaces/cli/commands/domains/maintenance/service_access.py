"""Owner-only accessors for maintenance CLI service wiring.

This module keeps first-party callers off retained public facades while the
top-level maintenance command and composition API remain stable external seams.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from importlib import import_module
from typing import TYPE_CHECKING, cast

from bioetl.composition.contracts import BronzeCleanupServiceProtocol

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.cleanup_service import CleanupPreview
    from bioetl.application.services.contracts.contract_migration_service import (
        ContractMigrationService,
    )
    from bioetl.application.services.ops.bronze_cleanup_service import (
        BronzeCleanupService,
    )
    from bioetl.application.services.ops.vacuum_service import VacuumService
    from bioetl.composition.contracts import MedallionLifecycleServiceProtocol

__all__ = [
    "get_bronze_cleanup_service",
    "get_contract_migration_service",
    "get_lifecycle_service",
    "get_vacuum_service",
    "preview_cleanup",
]

_ENTRYPOINTS_MODULE = "bioetl.composition.entrypoints"


def get_lifecycle_service() -> MedallionLifecycleServiceProtocol:
    """Load the lifecycle service through composition on demand."""
    _impl = import_module(_ENTRYPOINTS_MODULE).get_lifecycle_service
    return _impl()


def get_vacuum_service() -> VacuumService:
    """Load the vacuum service through composition on demand."""
    _impl = import_module(_ENTRYPOINTS_MODULE).get_vacuum_service
    return _impl()


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Load the bronze cleanup service through composition on demand."""
    candidate = import_module(_ENTRYPOINTS_MODULE).resolve(BronzeCleanupServiceProtocol)
    return cast("BronzeCleanupService", candidate)


def get_contract_migration_service() -> ContractMigrationService:
    """Load the contract migration service through composition on demand."""
    _impl = import_module(_ENTRYPOINTS_MODULE).get_contract_migration_service
    return _impl()


async def preview_cleanup(pipeline: str) -> CleanupPreview:
    """Preview pipeline cleanup through the maintenance composition seam."""
    _impl = import_module(_ENTRYPOINTS_MODULE).preview_cleanup
    impl = cast("Callable[[str], Awaitable[CleanupPreview]]", _impl)
    return await impl(pipeline)
