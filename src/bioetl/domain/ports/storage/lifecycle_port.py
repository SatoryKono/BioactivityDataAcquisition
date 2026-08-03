"""Storage lifecycle port for resource management."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.types import HealthStatus

__all__ = ["StorageLifecyclePort"]


@runtime_checkable
class StorageLifecyclePort(Protocol):
    """Port for storage resource lifecycle management.

    Covers graceful shutdown and health checking.
    """

    async def aclose(self) -> None:
        """Gracefully close the storage connection and release resources."""
        ...

    async def health_check(self) -> HealthStatus:
        """Check storage accessibility and basic write capability.

        Validates:
        - Bronze, Silver, Gold directories exist or can be created
        - Directories are writable

        Returns:
            HealthStatus indicating storage health:
            - HEALTHY: All layers accessible and writable
            - DEGRADED: Partial access (some layers unavailable)
            - UNHEALTHY: Storage completely unavailable
        """
        ...
