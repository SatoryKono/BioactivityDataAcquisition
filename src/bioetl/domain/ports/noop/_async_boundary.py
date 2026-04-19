"""Private async boundary helpers for no-op async port implementations."""

from __future__ import annotations

from collections.abc import Generator


class _ImmediateAwaitable:
    """Trivial awaitable used to preserve async port contracts."""

    def __await__(self) -> Generator[None, None, None]:
        if False:
            yield None
        return None


async def noop_async_boundary() -> None:
    """Introduce an await point without importing runtime I/O primitives."""
    await _ImmediateAwaitable()
