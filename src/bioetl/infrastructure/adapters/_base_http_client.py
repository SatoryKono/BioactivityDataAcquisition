"""Structural HTTP client seam used by BaseHttpAdapter."""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Protocol, Self

if TYPE_CHECKING:
    from bioetl.domain.ports import CircuitBreakerPort

__all__ = ["_HttpClientWithCircuitBreaker"]


class _HttpClientWithCircuitBreaker(Protocol):
    """Structural seam for the shared HTTP client used by adapters."""

    circuit_breaker: CircuitBreakerPort

    async def __aenter__(self) -> Self:
        """Enter the client context."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the client context."""
        ...
