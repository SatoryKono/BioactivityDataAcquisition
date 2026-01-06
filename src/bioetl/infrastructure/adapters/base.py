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
from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort, NoOpMetrics
from bioetl.domain.ports.health_check import HealthCheckResult
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.error_handling import ErrorService
from bioetl.infrastructure.adapters.health_check_mixin import HealthCheckMixin
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class BaseHttpAdapter(HealthCheckMixin, DataSourcePort):
    """Base class for HTTP adapters.

    Enforces usage of UnifiedHTTPClient and standardizes lifecycle management.

    Uses Template Method pattern for health checks:
    - health_check(): Template method that handles try/except with observability
    - _probe_health(): Override for provider-specific health probe
    - _fallback_health_status(): Fallback using circuit breaker state

    Health Check Observability (via HealthCheckMixin):
    - SUCCESS: DEBUG log, success counter, latency histogram
    - FAILURE: WARNING log with details, failure counter, latency histogram

    Error Handling:
    - _error_handler: Provides unified error classification, logging, and wrapping

    Attributes:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        provider_name: Unique identifier for the data provider.
        logger: LoggerPort instance for structured logging.
        metrics: MetricsPort instance for metrics collection (defaults to NoOpMetrics).

    """

    http_client: UnifiedHTTPClient
    provider_name: str
    logger: LoggerPort
    metrics: MetricsPort | None  # Runtime-resolved to NoOpMetrics if None
    _error_handler: ErrorService

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize BaseAdapter.

        Args:
            http_client: HTTP client for requests.
            logger: LoggerPort instance for structured logging (required).
            metrics: MetricsPort instance for metrics collection (optional).
                    Defaults to NoOpMetrics if not provided.

        """
        self.http_client = http_client
        self.logger = logger
        self.metrics = metrics if metrics is not None else NoOpMetrics()
        self._error_handler = ErrorService(logger)

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

    async def health_check(self) -> HealthStatus:
        """Check API health status using Template Method pattern.

        Calls _probe_health() for provider-specific probe, falling back
        to _fallback_health_status() on any exception.

        Observability (via HealthCheckMixin):
        - SUCCESS: DEBUG log, success counter, latency histogram
        - FAILURE: WARNING log with details, failure counter, latency histogram

        Returns:
            HealthStatus from probe or fallback.

        """
        ctx = self._start_health_check()
        try:
            status = await self._probe_health()
            self._handle_health_check_success(ctx, status)
            return status
        except Exception as e:
            fallback_status = self._fallback_health_status()
            # Log and record metrics for the failure
            self._handle_health_check_failure(ctx, e)
            return fallback_status

    async def check_health(self) -> HealthCheckResult:
        """Perform health check and return detailed result.

        This method provides enhanced health check with latency tracking
        and error details. It wraps the Template Method pattern used by
        health_check() with additional metrics.

        Observability (via HealthCheckMixin):
        - SUCCESS: DEBUG log, success counter, latency histogram
        - FAILURE: WARNING log with details, failure counter, latency histogram

        Returns:
            HealthCheckResult with status, latency, and error details.

        Note:
            This method never raises exceptions. All errors are caught
            and returned as UNHEALTHY status with error details.

        """
        ctx = self._start_health_check()
        last_error: str | None = None
        consecutive_failures = 0

        try:
            status = await self._probe_health()
            self._handle_health_check_success(ctx, status)
        except Exception as e:
            last_error = str(e)
            status = self._fallback_health_status()
            # Log and record metrics for the failure
            self._handle_health_check_failure(ctx, e)
            # Get failure count from circuit breaker if available
            try:
                consecutive_failures = (
                    self.http_client.circuit_breaker.get_failure_count()
                )
            except Exception:
                consecutive_failures = 1

        latency_ms = ctx.elapsed_seconds * 1000

        return HealthCheckResult(
            status=status,
            latency_ms=latency_ms,
            provider=self.provider_name,
            endpoint=self._get_health_endpoint(),
            last_error=last_error,
            consecutive_failures=consecutive_failures,
        )

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

    def _get_error_context(self, operation: str) -> dict[str, Any]:
        """Build error context with circuit breaker info.

        Args:
            operation: Operation name for context.

        Returns:
            Context dictionary for error handling.
        """
        try:
            cb_state = self.http_client.circuit_breaker.get_state().value
            cb_failures = self.http_client.circuit_breaker.get_failure_count()
        except Exception:
            cb_state = None
            cb_failures = 0

        return {
            "circuit_breaker_state": cb_state,
            "circuit_breaker_failures": cb_failures,
        }
