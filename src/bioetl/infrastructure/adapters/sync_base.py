"""Base Sync Adapter for BioETL infrastructure.

Provides common functionality for adapters that must use synchronous libraries
(like pubchempy) but need to integrate with the async architecture.

Uses Template Method pattern for health checks: subclasses implement
_probe_health() for provider-specific probes, with automatic fallback
to circuit breaker assessment on failure.
"""

from __future__ import annotations

import asyncio
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Self

from bioetl.domain.ports import DataSourcePort, LoggerPort
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket


class BaseSyncAdapter(DataSourcePort):
    """Base class for adapters using synchronous libraries.

    Manages a ThreadPoolExecutor, RateLimiter, and CircuitBreaker.

    Uses Template Method pattern for health checks:
    - health_check(): Template method that handles try/except
    - _probe_health(): Override for provider-specific health probe
    - _fallback_health_status(): Fallback using circuit breaker state

    Attributes:
        provider_name: Unique identifier for the data provider.
        logger: LoggerPort instance for structured logging.
        rate_limiter: Token bucket rate limiter.
        circuit_breaker: Circuit breaker for fault tolerance.
        thread_pool: Thread pool for executing sync code.

    """

    provider_name: str
    logger: LoggerPort
    rate_limiter: TokenBucket
    circuit_breaker: CircuitBreaker
    thread_pool: ThreadPoolExecutor

    def __init__(
        self,
        rate: float,
        logger: LoggerPort,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 300,
        max_workers: int = 4,
        strict_error_handling: bool = False,
    ) -> None:
        """Initialize Sync Adapter resources.

        Args:
            rate: Requests per second.
            logger: LoggerPort instance for structured logging.
            circuit_breaker_threshold: Failures before opening circuit.
            circuit_breaker_timeout: Recovery timeout in seconds.
            max_workers: Thread pool size.
            strict_error_handling: Whether to raise exceptions or log warnings.

        """
        self.logger = logger
        self.strict_error_handling = strict_error_handling

        # Common infrastructure components
        self.rate_limiter = TokenBucket(rate=rate, capacity=int(rate * 2))
        self.circuit_breaker = CircuitBreaker(
            provider=self.provider_name,
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_breaker_timeout,
        )
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)

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
