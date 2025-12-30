"""Base Sync Adapter for BioETL infrastructure.

Provides common functionality for adapters that must use synchronous libraries
(like pubchempy) but need to integrate with the async architecture.

Uses Template Method pattern for health checks: subclasses implement
_probe_health() for provider-specific probes, with automatic fallback
to circuit breaker assessment on failure.

Error Handling (RULES.md §4.1):
- Critical errors: Fail immediately (401, 403)
- Recoverable errors: Handled by circuit breaker
- Data quality errors: Log and skip record
"""

from __future__ import annotations

import asyncio
import time
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort, NoOpMetrics
from bioetl.domain.ports.health_check import HealthCheckResult
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.error_handling import ErrorHandler
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket


class BaseSyncAdapter(DataSourcePort):
    """Base class for adapters using synchronous libraries.

    Manages a ThreadPoolExecutor, RateLimiter, and CircuitBreaker.
    All dependencies are injected via constructor (Composition Root pattern).

    Uses Template Method pattern for health checks:
    - health_check(): Template method that handles try/except
    - _probe_health(): Override for provider-specific health probe
    - _fallback_health_status(): Fallback using circuit breaker state

    Error Handling:
    - _error_handler: Provides unified error classification, logging, and wrapping
    - _handle_adapter_error(): Template method for consistent error handling

    Attributes:
        provider_name: Unique identifier for the data provider.
        logger: LoggerPort instance for structured logging.
        metrics: MetricsPort instance for metrics collection.
        rate_limiter: Token bucket rate limiter (injected).
        circuit_breaker: Circuit breaker for fault tolerance (injected).
        thread_pool: Thread pool for executing sync code (injected).

    """

    provider_name: str
    logger: LoggerPort
    metrics: MetricsPort
    rate_limiter: TokenBucket
    circuit_breaker: CircuitBreaker
    thread_pool: ThreadPoolExecutor
    _error_handler: ErrorHandler

    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
        strict_error_handling: bool = False,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize Sync Adapter resources.

        All infrastructure components are injected from Composition Root.

        Args:
            logger: LoggerPort instance for structured logging.
            rate_limiter: Pre-configured token bucket rate limiter.
            circuit_breaker: Pre-configured circuit breaker.
            thread_pool: Pre-configured thread pool executor.
            strict_error_handling: Whether to raise exceptions or log warnings.
            metrics: MetricsPort instance for metrics collection.

        """
        self.logger = logger
        self.metrics = metrics if metrics is not None else NoOpMetrics()
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.thread_pool = thread_pool
        self.strict_error_handling = strict_error_handling
        self._error_handler = ErrorHandler(logger)

        # Safety: ensure shutdown if aclose/context manager is misused
        self._finalizer = weakref.finalize(self, self.thread_pool.shutdown, wait=False)

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.close()

    async def close(self) -> None:
        """Close thread pool."""
        self.thread_pool.shutdown(wait=True)

    async def aclose(self) -> None:
        """Gracefully close resources."""
        await self.close()

    async def _run_in_executor(self, func: Any, *args: Any) -> Any:
        """Run synchronous function in thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args)

    async def health_check(self) -> HealthStatus:
        """Check API health status using Template Method pattern.

        Calls _probe_health() for provider-specific probe, falling back
        to _fallback_health_status() on any exception. Logs warning and
        increments failure metric on exception.

        Returns:
            HealthStatus from probe or fallback.

        """
        try:
            return await self._probe_health()
        except Exception as e:
            self.logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            self.metrics.increment_counter(
                "health_check_failures_total",
                1,
                {"provider": self.provider_name},
            )
            return self._fallback_health_status()

    async def check_health(self) -> HealthCheckResult:
        """Perform health check with latency tracking. Never raises; returns UNHEALTHY on errors."""
        start_time = time.monotonic()
        last_error: str | None = None
        consecutive_failures = 0

        try:
            status = await self._probe_health()
        except Exception as e:
            last_error = str(e)
            status = self._fallback_health_status()
            self.logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            self.metrics.increment_counter(
                "health_check_failures_total",
                1,
                {"provider": self.provider_name},
            )
            # Get failure count from circuit breaker
            try:
                consecutive_failures = self.circuit_breaker.get_failure_count()
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

        Subclasses SHOULD override this with a specific API call.
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
            return assess_health_from_circuit_breaker(self.circuit_breaker)
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
            cb_state = self.circuit_breaker.get_state().value
            cb_failures = self.circuit_breaker.get_failure_count()
        except Exception:
            cb_state = None
            cb_failures = 0

        return {
            "circuit_breaker_state": cb_state,
            "circuit_breaker_failures": cb_failures,
        }

    def _handle_adapter_error(
        self,
        error: Exception,
        operation: str = "fetch",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Handle adapter error with unified logging and wrapping.

        Logs error with full context and raises appropriate exception.
        Uses ErrorHandler for consistent behavior across all adapters.

        Args:
            error: The exception that occurred.
            operation: Operation that failed (e.g., 'fetch', 'health_check').
            context: Additional context (status_code, retry_count, etc.).

        Raises:
            CriticalError: For authentication failures (401, 403).
            ExternalServiceError: For other errors.
        """
        ctx = self._get_error_context(operation)
        if context:
            ctx.update(context)

        # Let ErrorHandler log and wrap the error
        wrapped = self._error_handler.handle_error(
            error=error,
            provider=self.provider_name,
            operation=operation,
            context=ctx,
        )
        raise wrapped from error
