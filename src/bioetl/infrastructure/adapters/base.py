"""Base HTTP adapter for BioETL infrastructure.

Provides common functionality for adapters interacting with HTTP APIs,
including lifecycle management (context manager) and health checks.

Uses Template Method pattern for health checks: subclasses implement
_probe_health() for provider-specific probes, with automatic fallback
to circuit breaker assessment on failure.

Error Handling (RULES.md §4.1):
- Critical errors: Fail immediately (401, 403)
- Recoverable errors: Handled by UnifiedHTTPClient retry
- Data quality errors: Log and skip record

Health Check Observability (RULES.md §4.8):
- SUCCESS: DEBUG log "health_check_passed", increment success counter
- FAILURE: WARNING log "health_check_failed" with details, increment failure counter
- LATENCY: Record duration histogram for all health checks
"""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort, NoOpMetrics
from bioetl.infrastructure.adapters.error_handling import ErrorService
from bioetl.infrastructure.adapters.health_check_mixin import HealthCheckProviderMixin

if TYPE_CHECKING:
    from bioetl.domain.ports import CircuitBreakerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class BaseHttpAdapter(HealthCheckProviderMixin, DataSourcePort):
    """Base class for HTTP adapters.

    Enforces usage of UnifiedHTTPClient and standardizes lifecycle management.

    Uses Template Method pattern for health checks via HealthCheckProviderMixin:
    - health_check(): Template method that handles try/except with observability
    - _probe_health(): Override for provider-specific health probe
    - _fallback_health_status(): Fallback using circuit breaker state

    Health Check Observability (via HealthCheckProviderMixin):
    - SUCCESS: DEBUG log, success counter, latency histogram
    - FAILURE: WARNING log with details, failure counter, latency histogram

    Error Handling:
    - _error_handler: Provides unified error classification, logging, and wrapping

    Attributes:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        provider_name: Unique identifier for the data provider.
        logger: LoggerPort instance for structured logging.
        metrics: MetricsPort instance for metrics collection (defaults to NoOpMetrics).
        circuit_breaker: CircuitBreakerPort instance (optional, for health checks).

    """

    http_client: UnifiedHTTPClient
    provider_name: str
    logger: LoggerPort
    metrics: MetricsPort | None  # Runtime-resolved to NoOpMetrics if None
    circuit_breaker: CircuitBreakerPort | None
    _error_handler: ErrorService

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
        circuit_breaker: CircuitBreakerPort | None = None,
    ) -> None:
        """Initialize BaseAdapter.

        Args:
            http_client: HTTP client for requests.
            logger: LoggerPort instance for structured logging (required).
            metrics: MetricsPort instance for metrics collection (optional).
                    Defaults to NoOpMetrics if not provided.
            circuit_breaker: CircuitBreakerPort for health status assessment.

        """
        self.http_client = http_client
        self.logger = logger
        self.metrics = metrics if metrics is not None else NoOpMetrics()
        self.circuit_breaker = circuit_breaker
        self._error_handler = ErrorService(logger)

    @property
    def _circuit_breaker(self) -> CircuitBreakerPort:
        """Return circuit breaker.

        Implements abstract property from HealthCheckProviderMixin.

        Returns:
            CircuitBreakerPort instance for health status assessment.

        Raises:
            RuntimeError: If circuit breaker is not configured.
        """
        if self.circuit_breaker:
            return self.circuit_breaker
        raise RuntimeError(f"Circuit Breaker not configured for adapter {self.provider_name}")

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
