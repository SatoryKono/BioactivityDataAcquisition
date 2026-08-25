"""Health-service application ports (ADR-058)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.services.ops.health_service import HealthCheckSummary


class HealthServiceProtocol(Protocol):
    """Provider-health orchestration used by first-party interfaces."""

    async def check_providers(
        self,
        providers: list[str] | None = None,
    ) -> HealthCheckSummary:
        """Check the requested providers, or every registered provider."""
        ...
