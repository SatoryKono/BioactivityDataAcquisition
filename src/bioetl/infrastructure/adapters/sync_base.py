# pyright: reportImplicitAbstractClass=false
# pyright: reportIncompatibleMethodOverride=false
# MRO/override residual on mixin or client hierarchies.
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
- HEALTHY: DEBUG log "health_check_passed", increment healthy counter
- DEGRADED: WARNING log "health_check_degraded", increment degraded counter
- FAILED/UNHEALTHY: WARNING log "health_check_failed"/"health_check_unhealthy", increment failure counter
- LATENCY: Record duration histogram for all health checks
"""

from __future__ import annotations

__all__ = ["BaseSyncAdapter"]

import asyncio
import weakref
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.ports import (
    DataSourcePort,
    ErrorHandlerPort,
    LoggerPort,
    MetricsPort,
)
from bioetl.infrastructure.adapters.health_check_mixin import HealthCheckProviderMixin

if TYPE_CHECKING:
    from bioetl.domain.ports import CircuitBreakerPort
    from bioetl.infrastructure.adapters.common import SyncAdapterDependencyContext
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter


class BaseSyncAdapter(HealthCheckProviderMixin, DataSourcePort):
    """Base class for adapters using synchronous libraries.

    Manages a ThreadPoolExecutor, RateLimiter, and CircuitBreakerGuard.
    All dependencies are injected via constructor (Composition Root pattern).

    Uses Template Method pattern for health checks via HealthCheckProviderMixin:
    - health_check(): Template method that handles try/except with observability
    - _probe_health(): Override for provider-specific health probe
    - _fallback_health_status(): Fallback using circuit breaker state

    Health Check Observability (via HealthCheckProviderMixin):
    - HEALTHY: DEBUG log, healthy counter, latency histogram
    - DEGRADED: WARNING log, degraded counter, latency histogram
    - FAILED/UNHEALTHY: WARNING log with details, failure counter, latency histogram

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
    metrics: MetricsPort | None
    rate_limiter: TokenBucketRateLimiter
    circuit_breaker: CircuitBreakerGuard
    thread_pool: ThreadPoolExecutor
    _error_handler: ErrorHandlerPort
    _owns_thread_pool: bool

    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
        error_handler: ErrorHandlerPort,
        strict_error_handling: bool = False,
        dependency_context: SyncAdapterDependencyContext | None = None,
        owns_thread_pool: bool = False,
        **legacy: object,
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
            dependency_context: Explicit composition-owned dependency bundle for
                sync adapter runtime collaborators. When provided, its metrics
                and error handler take precedence over legacy named arguments.
            error_handler: Pre-built error handler injected by the
                composition root.
            owns_thread_pool: Whether this adapter owns the injected executor and
                should shut it down on ``close()``/GC finalization. Defaults to
                ``False`` so externally managed executors are not closed implicitly.

        """
        metrics = legacy.pop("metrics", None)
        if legacy:
            unexpected = ", ".join(sorted(str(k) for k in legacy))
            raise TypeError(f"BaseSyncAdapter() unexpected kwargs: {unexpected}")
        from typing import cast

        legacy_metrics = cast("MetricsPort | None", metrics)
        metrics_port = (
            dependency_context.metrics
            if dependency_context is not None
            else legacy_metrics
        )
        resolved_error_handler = (
            dependency_context.error_handler
            if dependency_context is not None
            else error_handler
        )
        self.logger = logger
        self._logger = logger  # Private alias required by HealthCheckMixin
        self.metrics = metrics_port
        self.rate_limiter = rate_limiter
        self.circuit_breaker = circuit_breaker
        self.thread_pool = thread_pool
        self._owns_thread_pool = owns_thread_pool
        self.strict_error_handling = strict_error_handling
        self._error_handler = resolved_error_handler

        # Safety: owned executors are finalized if explicit close is missed.
        self._finalizer = (
            weakref.finalize(self, self.thread_pool.shutdown, wait=False)
            if owns_thread_pool
            else None
        )

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

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.close()

    async def close(self) -> None:
        """Close owned executor resources."""
        if not self._owns_thread_pool:
            return
        if self._finalizer is not None and self._finalizer.alive:
            self._finalizer.detach()
        self.thread_pool.shutdown(wait=True)

    async def aclose(self) -> None:
        """Gracefully close resources."""
        await self.close()

    async def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> object:
        """Run synchronous function in thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args)
