"""Base HTTP adapter for BioETL infrastructure.

Provides common functionality for adapters interacting with HTTP APIs,
including lifecycle management (context manager) and health checks.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Self

from bioetl.domain.ports import DataSourcePort
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

logger = logging.getLogger(__name__)


class BaseHttpAdapter(DataSourcePort):
    """Base class for HTTP adapters.

    Enforces usage of UnifiedHTTPClient and standardizes lifecycle management.
    """

    http_client: UnifiedHTTPClient
    provider_name: str

    def __init__(self, http_client: UnifiedHTTPClient) -> None:
        self.http_client = http_client

    async def __aenter__(self) -> Self:
        """Enter async context manager.

        Delegates to the underlying HTTP client.
        """
        await self.http_client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager.

        Delegates to the underlying HTTP client.
        """
        await self.http_client.__aexit__(exc_type, exc_val, exc_tb)

    async def aclose(self) -> None:
        """Close resources.

        Base implementation is a no-op as HTTP client is managed by context.
        Subclasses can override if they manage additional resources.
        """
        pass

    async def health_check(self) -> HealthStatus:
        """Check API health status.

        Default implementation uses the circuit breaker state from the HTTP client.
        Subclasses SHOULD override this with a specific API call (e.g. /health).
        """
        try:
            return assess_health_from_circuit_breaker(self.http_client.circuit_breaker)
        except Exception:
            return HealthStatus.UNHEALTHY
