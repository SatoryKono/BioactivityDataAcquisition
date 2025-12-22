"""Base Sync Adapter for BioETL infrastructure.

Provides common functionality for adapters that must use synchronous libraries
(like pubchempy) but need to integrate with the async architecture.
"""

from __future__ import annotations

import asyncio
import logging
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Self

from bioetl.domain.ports import DataSourcePort
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

logger = logging.getLogger(__name__)


class BaseSyncAdapter(DataSourcePort):
    """Base class for adapters using synchronous libraries.

    Manages a ThreadPoolExecutor, RateLimiter, and CircuitBreaker.
    """

    provider_name: str
    rate_limiter: TokenBucket
    circuit_breaker: CircuitBreaker
    thread_pool: ThreadPoolExecutor

    def __init__(
        self,
        rate: float,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 300,
        max_workers: int = 4,
        strict_error_handling: bool = False,
    ) -> None:
        """Initialize Sync Adapter resources.

        Args:
            rate: Requests per second.
            circuit_breaker_threshold: Failures before opening circuit.
            circuit_breaker_timeout: Recovery timeout in seconds.
            max_workers: Thread pool size.
            strict_error_handling: Whether to raise exceptions or log warnings.
        """
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
        """Default health check based on Circuit Breaker state."""
        try:
            return assess_health_from_circuit_breaker(self.circuit_breaker)
        except Exception:
            return HealthStatus.UNHEALTHY
