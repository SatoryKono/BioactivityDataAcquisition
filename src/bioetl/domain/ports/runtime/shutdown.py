"""Shutdown port (Protocol) for graceful termination.

This port defines the contract for shutdown coordination across
pipeline components, following ADR-008 graceful shutdown strategy.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ShutdownPort(Protocol):
    """Port for coordinating graceful shutdown across pipeline components.

    This protocol defines the contract for shutdown coordination:
    - Signal initiation (from OS signals or internal triggers)
    - State checking (for components to check before operations)
    - Async waiting (for coordinated cleanup)

    Implementations:
    - ShutdownService: Application-layer service with full orchestration
    - ShutdownSignal: Lightweight coordination object (legacy)

    Example:
        async def process_batch(self, batch: list[dict]) -> None:
            if self._shutdown.is_shutting_down():
                return  # Skip processing
            await self._write_batch(batch)

    """

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been requested.

        Returns:
            True if shutdown was initiated, False otherwise.

        Note:
            Thread-safe. Can be called from any context.
        """
        ...

    async def initiate_shutdown(self, reason: str) -> None:
        """Initiate graceful shutdown with a reason.

        This method triggers the shutdown sequence:
        1. Sets shutdown flag
        2. Notifies waiting components via asyncio.Event
        3. Logs the shutdown reason

        Args:
            reason: Human-readable reason for shutdown (e.g., "SIGTERM received",
                "Lock lost", "DQ threshold exceeded").

        Note:
            Idempotent - multiple calls have no additional effect.
        """
        ...

    async def wait_for_completion(self, timeout_seconds: float) -> bool:
        """Wait for shutdown completion with timeout.

        Blocks until either:
        - All cleanup operations complete
        - Timeout expires

        Args:
            timeout_seconds: Maximum seconds to wait for completion.

        Returns:
            True if shutdown completed within timeout, False if timeout expired.

        Raises:
            asyncio.TimeoutError: If wait_for_completion is not supported
                and timeout expires (implementation-specific).
        """
        ...


__all__ = ["ShutdownPort"]
