"""Base HTTP adapter for BioETL infrastructure.

Provides common functionality for adapters interacting with HTTP APIs,
including lifecycle management (context manager), health checks, and
unified error handling.

Uses Template Method pattern for health checks: subclasses implement
_probe_health() for provider-specific probes, with automatic fallback
to circuit breaker assessment on failure.

Error Handling (RULES.md §4.1):
All adapters use AdapterErrorHandler for unified error classification,
logging, and exception wrapping. This ensures consistent behavior:
- CRITICAL errors (401, 403): Fail immediately
- RECOVERABLE errors (429, 5xx): Retry with exponential backoff
- DATA_QUALITY errors: Log and skip record
"""

from __future__ import annotations

import time
from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.ports import DataSourcePort, LoggerPort
from bioetl.domain.ports.health_check import HealthCheckResult
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.error_handling import AdapterErrorHandler
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

    Provides unified error handling via AdapterErrorHandler:
    - _error_handler: Lazily initialized error handler
    - Use _error_handler.handle_error() in catch blocks

    Attributes:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        provider_name: Unique identifier for the data provider.
        logger: LoggerPort instance for structured logging.

    """

    http_client: UnifiedHTTPClient
    provider_name: str
    logger: LoggerPort

    # Lazily initialized error handler
    _error_handler_instance: AdapterErrorHandler | None = None

    def __init__(self, http_client: UnifiedHTTPClient, logger: LoggerPort) -> None:
        """Initialize BaseAdapter.

        Args:
            http_client: HTTP client for requests.
            logger: LoggerPort instance for structured logging (required).

        """
        self.http_client = http_client
        self.logger = logger
        self._error_handler_instance = None

    @property
    def _error_handler(self) -> AdapterErrorHandler:
        """Get or create error handler (lazy initialization).

        Returns:
            AdapterErrorHandler configured for this adapter.
        """
        if self._error_handler_instance is None:
            self._error_handler_instance = AdapterErrorHandler(
                logger=self.logger,
                provider=self.provider_name,
                circuit_breaker=getattr(self.http_client, "circuit_breaker", None),
            )
        return self._error_handler_instance

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

    async def check_health(self) -> HealthCheckResult:
        """Perform health check and return detailed result.

        This method provides enhanced health check with latency tracking
        and error details. It wraps the Template Method pattern used by
        health_check() with additional metrics.

        Returns:
            HealthCheckResult with status, latency, and error details.

        Note:
            This method never raises exceptions. All errors are caught
            and returned as UNHEALTHY status with error details.

        """
        start_time = time.monotonic()
        last_error: str | None = None
        consecutive_failures = 0

        try:
            status = await self._probe_health()
        except Exception as e:
            last_error = str(e)
            status = self._fallback_health_status()
            # Get failure count from circuit breaker if available
            try:
                consecutive_failures = (
                    self.http_client.circuit_breaker.get_failure_count()
                )
            except Exception:
                consecutive_failures = 1

        latency_ms = (time.monotonic() - start_time) * 1000

        return HealthCheckResult(
            status=status,
            latency_ms=latency_ms,
            provider=self.provider_name,
            endpoint=self._get_health_endpoint(),
            last_error=last_error,
            consecutive_failures=consecutive_failures,
        )

    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint for this adapter.

        Subclasses SHOULD override this to return the specific endpoint
        used for health probes. Default returns empty string.

        Returns:
            Health check endpoint path.

        """
        return ""

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
