"""Shared fetch flow service for PubChem strategy execution."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

import pubchempy as pcp

from bioetl.domain.resilience import RetryConfig

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

__all__ = ["PubChemFetchFlow"]


class _RequestRecorder(Protocol):
    def __call__(
        self,
        endpoint: str,
        duration_ms: float,
        status_code: int = 200,
        result_count: int = 0,
    ) -> None: ...


@dataclass(slots=True)
class PubChemFetchFlow:
    """Execute PubChem API fetches with timing, limiter, breaker and telemetry."""

    rate_limiter: TokenBucketRateLimiter
    circuit_breaker: CircuitBreakerGuard
    run_in_executor: Callable[..., Awaitable[object]]
    record_request: _RequestRecorder
    normalize_results: Callable[[object], list[object]]
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    logger: LoggerPort | None = None

    async def execute(
        self,
        *,
        endpoint: str,
        pubchem_callable: Callable[..., object],
        pubchem_args: tuple[object, ...],
    ) -> list[object]:
        """Retry transient SDK HTTP failures within the configured request budget."""
        attempt = 0
        while True:
            await self.rate_limiter.acquire()
            start_time = time.perf_counter()
            try:
                raw_results = await self.circuit_breaker.call(
                    self.run_in_executor,
                    pubchem_callable,
                    *pubchem_args,
                )
            except pcp.PubChemHTTPError as error:
                self.record_request(
                    endpoint,
                    (time.perf_counter() - start_time) * 1000,
                    status_code=error.code,
                )
                attempt += 1
                if (
                    attempt >= self.retry_config.max_attempts
                    or not self.retry_config.is_retryable_status(error.code)
                ):
                    raise
                delay = self.retry_config.calculate_delay(attempt - 1, endpoint)
                if self.logger is not None:
                    self.logger.warning(
                        "pubchem_request_retry",
                        provider="pubchem",
                        endpoint=endpoint,
                        status_code=error.code,
                        attempt=attempt,
                        max_attempts=self.retry_config.max_attempts,
                        wait_seconds=delay,
                    )
                await asyncio.sleep(delay)
                continue
            normalized = self.normalize_results(raw_results)
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.record_request(endpoint, duration_ms, result_count=len(normalized))
            return normalized
