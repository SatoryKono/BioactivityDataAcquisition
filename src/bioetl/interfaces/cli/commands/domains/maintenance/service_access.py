"""Owner-only accessors for maintenance CLI service wiring.

This module keeps first-party callers off retained public facades while the
top-level maintenance command and composition API remain stable external seams.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.cleanup_service import CleanupPreview
    from bioetl.application.services.bronze_cleanup_service import (
        BronzeCleanupService,
    )
    from bioetl.application.services.contract_migration_service import (
        ContractMigrationService,
    )
    from bioetl.application.services.vacuum_service import VacuumService
    from bioetl.composition._resource_management import (
        MedallionLifecycleServiceProtocol,
    )

__all__ = [
    "get_bronze_cleanup_service",
    "get_contract_migration_service",
    "get_lifecycle_service",
    "get_vacuum_service",
    "preview_cleanup",
]


def get_lifecycle_service() -> MedallionLifecycleServiceProtocol:
    """Load the lifecycle service through composition on demand."""
    from bioetl.composition.maintenance_service_access import (
        get_lifecycle_service as _impl,
    )

    return _impl()


def get_vacuum_service() -> VacuumService:
    """Load the vacuum service through composition on demand."""
    from bioetl.composition.maintenance_service_access import (
        get_vacuum_service as _impl,
    )

    return _impl()


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Load the bronze cleanup service through composition on demand."""
    from bioetl.composition.maintenance_service_access import (
        get_bronze_cleanup_service as _impl,
    )

    return _impl()


def get_contract_migration_service() -> ContractMigrationService:
    """Load the contract migration service through composition on demand."""
    from bioetl.composition.maintenance_service_access import (
        get_contract_migration_service as _impl,
    )

    return _impl()


async def preview_cleanup(pipeline: str) -> CleanupPreview:
    """Preview pipeline cleanup through the maintenance composition seam."""
    from bioetl.composition.maintenance_service_access import preview_cleanup as _impl

    impl = cast("Callable[[str], Awaitable[CleanupPreview]]", _impl)
    return await impl(pipeline)
