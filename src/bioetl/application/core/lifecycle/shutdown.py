"""Shutdown coordination for pipeline components.

This module provides backward-compatible ShutdownSignal that implements
ShutdownPort protocol. For new code, prefer using ShutdownService from
application/services/shutdown_service.py.

See ADR-008 for graceful shutdown strategy details.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# Re-export from new location for backward compatibility
from bioetl.application.services.shutdown_service import (
    PipelineShutdownError,
    ShutdownReason,
    ShutdownService,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


@dataclass
class ShutdownSignal:
    """Shared signal for coordinating graceful shutdown.
    This class implements ShutdownPort protocol and can be used
    interchangeably with ShutdownService.
    For new code, prefer ShutdownService which provides:
    - Detailed reason tracking
    - Metrics emission
    - Completion waiting
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
    _completion_event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _reason: str = field(default="", init=False)

    @property
    def is_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._requested

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been requested (ShutdownPort compatible).
        Returns:
            True if the condition is met, False otherwise.
        """
        return self._requested

    def request(self) -> None:
        """Request graceful shutdown.
        All components watching this signal will be notified.
        This method is idempotent - multiple calls have no additional effect.
        """
        if not self._requested:
            self._requested = True
            self._event.set()

    async def initiate_shutdown(self, reason: str) -> None:
        """Initiate graceful shutdown (ShutdownPort compatible).
        Args:
            reason: Human-readable reason for shutdown.
        """
        await asyncio.sleep(0)
        if not self._requested:
            self._requested = True
            self._reason = reason
            self._event.set()

    async def wait(self) -> None:
        """Wait until shutdown is requested.
        Blocks until request() is called. Use with asyncio.wait_for()
        for timeout-based waiting.
        """
        await self._event.wait()

    async def wait_for_completion(self, timeout_seconds: float) -> bool:
        """Wait for shutdown completion (ShutdownPort compatible).
        Args:
            timeout_seconds: Maximum seconds to wait.
        Returns:
            True if completed within timeout, False otherwise.
        """
        try:
            async with asyncio.timeout(timeout_seconds):
                await self._completion_event.wait()
            return True
        except TimeoutError:
            return False

    def mark_completed(self) -> None:
        """Mark shutdown as completed."""
        self._completion_event.set()

    def reset(self) -> None:
        """Reset signal for reuse (e.g., in tests).
        Warning: Only use in tests or when you're certain no components
        are currently checking the signal.
        """
        self._requested = False
        self._event.clear()
        self._completion_event.clear()
        self._reason = ""


def create_shutdown_service(
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
) -> ShutdownService:
    """Factory function to create ShutdownService.
    Convenience function for creating ShutdownService with
    proper dependency injection.
    Args:
        logger: Logger for shutdown events.
        metrics: Optional metrics port for shutdown metrics.
    Returns:
        Configured ShutdownService instance.
    """
    return ShutdownService(logger=logger, metrics=metrics)


__all__ = [
    "PipelineShutdownError",
    "ShutdownReason",
    "ShutdownService",
    "ShutdownSignal",
    "create_shutdown_service",
]
