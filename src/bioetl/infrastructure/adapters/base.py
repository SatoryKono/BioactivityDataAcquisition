"""Base HTTP adapter for BioETL infrastructure.

Provides common functionality for adapters interacting with HTTP APIs,
including lifecycle management (context manager) and health checks.

Uses Template Method pattern for health checks: subclasses implement
_probe_health() for provider-specific probes, with automatic fallback
to circuit breaker assessment on failure.
"""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.ports import DataSourcePort, LoggerPort
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class BaseHttpAdapter(DataSourcePort):
    """Base class for HTTP adapters.

    Enforces usage of UnifiedHTTPClient and standardizes lifecycle management.

    Uses Template Method pattern for health checks:
    - health_check(): Template method that handles try/except
    - _probe_health(): Override for provider-specific health probe
    - _fallback_health_status(): Fallback using circuit breaker state

    Attributes:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        provider_name: Unique identifier for the data provider.
        logger: LoggerPort instance for structured logging.

    """

    http_client: UnifiedHTTPClient
    provider_name: str
    logger: LoggerPort

    def __init__(self, http_client: UnifiedHTTPClient, logger: LoggerPort) -> None:
        """Initialize BaseAdapter.

        Args:
            http_client: HTTP client for requests.
            logger: LoggerPort instance for structured logging (required).

        """
        self.http_client = http_client
        self.logger = logger

    async def __aenter__(self) -> Self:
        """Enter async context manager.

        Delegates to the underlying HTTP client.
        """
        await self.http_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
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
        """Check API health status using Template Method pattern.

        Calls _probe_health() for provider-specific probe, falling back
        to _fallback_health_status() on any exception.

        Returns:
            HealthStatus from probe or fallback.

        """
        try:
            return await self._probe_health()
        except Exception:
            return self._fallback_health_status()

    async def _probe_health(self) -> HealthStatus:
        """Perform provider-specific health probe.

        Subclasses SHOULD override this with a specific API call (e.g. /health).
        Default implementation returns fallback health status.

        Returns:
            HealthStatus from the health probe.

        """
        return self._fallback_health_status()

    def _fallback_health_status(self) -> HealthStatus:
        """Get health status from circuit breaker state.

        Used as fallback when _probe_health() fails or is not implemented.

        Returns:
            HealthStatus based on circuit breaker state.

        """
        try:
            return assess_health_from_circuit_breaker(self.http_client.circuit_breaker)
        except Exception:
            return HealthStatus.UNHEALTHY
