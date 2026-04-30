"""Shared fetch flow service for PubChem strategy execution."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

__all__ = ["PubChemFetchFlow", "PubChemFetchFlowService"]


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

    async def execute(
        self,
        *,
        endpoint: str,
        pubchem_callable: Callable[..., object],
        pubchem_args: tuple[object, ...],
    ) -> list[object]:
        """Execute single PubChem call and return normalized results."""
        await self.rate_limiter.acquire()
        start_time = time.perf_counter()
        raw_results = await self.circuit_breaker.call(
            self.run_in_executor,
            pubchem_callable,
            *pubchem_args,
        )
        normalized = self.normalize_results(raw_results)
        duration_ms = (time.perf_counter() - start_time) * 1000
        self.record_request(endpoint, duration_ms, result_count=len(normalized))
        return normalized


PubChemFetchFlowService = PubChemFetchFlow
