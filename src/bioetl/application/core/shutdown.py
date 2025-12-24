"""Shutdown coordination for pipeline components.

This module provides a shared shutdown signal that can be passed to
multiple pipeline components without creating circular dependencies.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class ShutdownSignal:
    """Shared signal for coordinating graceful shutdown.

    This object is passed to pipeline components to allow them to:
    1. Check if shutdown was requested
    2. Request shutdown (e.g., when lock is lost)
    3. Wait for shutdown signal

    Thread-safe via asyncio.Event.

    Example:
        >>> signal = ShutdownSignal()
        >>> # In orchestrator
        >>> signal.request()
        >>> # In executor
        >>> if signal.is_requested:
        ...     await checkpoint_manager.save()

    """

    _requested: bool = field(default=False, init=False)
    _event: asyncio.Event = field(default_factory=asyncio.Event, init=False)

    @property
    def is_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._requested

    def request(self) -> None:
        """Request graceful shutdown.

        All components watching this signal will be notified.
        This method is idempotent - multiple calls have no additional effect.
        """
        if not self._requested:
            self._requested = True
            self._event.set()

    async def wait(self) -> None:
        """Wait until shutdown is requested.

        Blocks until request() is called. Use with asyncio.wait_for()
        for timeout-based waiting.
        """
        await self._event.wait()

    def reset(self) -> None:
        """Reset signal for reuse (e.g., in tests).

        Warning: Only use in tests or when you're certain no components
        are currently checking the signal.
        """
        self._requested = False
        self._event.clear()


class PipelineShutdownError(Exception):
    """Raised when pipeline receives shutdown signal.

    This exception signals that the pipeline should gracefully terminate,
    saving any pending checkpoints before exit.
    """

    pass


__all__ = ["PipelineShutdownError", "ShutdownSignal"]
