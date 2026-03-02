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

Health Check Observability (RULES.md §4.8):
- SUCCESS: DEBUG log "health_check_passed", increment success counter
- FAILURE: WARNING log "health_check_failed" with details, increment failure counter
- LATENCY: Record duration histogram for all health checks
"""

from __future__ import annotations

import asyncio
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort, NoOpMetrics
from bioetl.infrastructure.adapters.error_handling import ErrorService
from bioetl.infrastructure.adapters.health_check_mixin import HealthCheckProviderMixin

if TYPE_CHECKING:
    from bioetl.domain.ports import CircuitBreakerPort
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket


class BaseSyncAdapter(HealthCheckProviderMixin, DataSourcePort):
    """Base class for adapters using synchronous libraries.

    Manages a ThreadPoolExecutor, RateLimiter, and CircuitBreaker.
    All dependencies are injected via constructor (Composition Root pattern).

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
        provider_name: Unique identifier for the data provider.
        logger: LoggerPort instance for structured logging.
        metrics: MetricsPort instance for metrics collection.
        rate_limiter: Token bucket rate limiter (injected).
        circuit_breaker: Circuit breaker for fault tolerance (injected).
        thread_pool: Thread pool for executing sync code (injected).

    """

    provider_name: str
    logger: LoggerPort
    metrics: MetricsPort | None  # Runtime-resolved to NoOpMetrics if None
    rate_limiter: TokenBucket
    circuit_breaker: CircuitBreaker
    thread_pool: ThreadPoolExecutor
    _error_handler: ErrorService

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
        self._error_handler = ErrorService(logger)

        # Safety: ensure shutdown if aclose/context manager is misused
        self._finalizer = weakref.finalize(self, self.thread_pool.shutdown, wait=False)

    @property
    def _circuit_breaker(self) -> CircuitBreakerPort:
        """Return circuit breaker instance.

        Implements abstract property from HealthCheckProviderMixin.

        Returns:
            CircuitBreakerPort instance for health status assessment.

        """
        return self.circuit_breaker

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    # Any: standard __aexit__ sig...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.close()

    async def close(self) -> None:
        """Close thread pool."""
        self.thread_pool.shutdown(wait=True)

    async def aclose(self) -> None:
        """Gracefully close resources."""
        await self.close()

    # Any: generic executor wrapp...
    async def _run_in_executor(self, func: Any, *args: Any) -> Any:
        """Run synchronous function in thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args)
