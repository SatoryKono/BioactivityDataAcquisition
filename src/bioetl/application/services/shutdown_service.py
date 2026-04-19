"""Shutdown Service for graceful pipeline termination.

This service consolidates all shutdown-related logic in one place,
implementing ADR-008 graceful shutdown strategy:
1. Stop fetching new records
2. Wait for current batch to complete
3. Save checkpoint
4. Release lock
5. Emit shutdown metrics

Follows RULES.md §5.3: At-Least-Once + deduplication guarantee.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.exceptions.pipeline_shutdown import (
    PipelineShutdownError,
    ShutdownReason,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


@dataclass
class ShutdownService:
    """Unified service for coordinating graceful shutdown.

    This service implements ShutdownPort and provides centralized
    shutdown coordination for all pipeline components.

    Responsibilities:
    - Maintain shutdown state (requested flag, asyncio.Event)
    - Provide async waiting for shutdown completion
    - Track shutdown reason and timing for observability
    - Emit metrics on shutdown initiation and completion

    The service does NOT directly manage resources (locks, checkpoints).
    Resource cleanup is delegated to their respective managers via
    context managers and the shutdown flag.

    Example:
        shutdown_service = ShutdownService(logger=logger, metrics=metrics)

        # In signal handler
        await shutdown_service.initiate_shutdown("SIGTERM received")

        # In executor loop
        if shutdown_service.is_shutting_down():
            await checkpoint_manager.save()
            break

        # Wait for graceful completion
        completed = await shutdown_service.wait_for_completion(timeout=30.0)

    """

    logger: LoggerPort
    metrics: MetricsPort | None = None

    # Internal state (not exposed via __init__)
    _requested: bool = field(default=False, init=False)
    _event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _completion_event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _reason: ShutdownReason = field(default=ShutdownReason.UNKNOWN, init=False)
    _reason_detail: str = field(default="", init=False)

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been requested.

        Returns:
            True if shutdown was initiated, False otherwise.

        Note:
            Thread-safe via asyncio.Event internal locking.
        """
        return self._requested

    @property
    def reason(self) -> ShutdownReason:
        """Get the reason for shutdown.

        Returns:
            ShutdownReason enum value, or UNKNOWN if not yet initiated.
        """
        return self._reason

    async def initiate_shutdown(self, reason: str) -> None:
        """Initiate graceful shutdown with a reason.

        This method:
        1. Sets the shutdown flag (idempotent)
        2. Parses reason to ShutdownReason enum
        3. Notifies waiting components via asyncio.Event
        4. Logs the shutdown initiation
        5. Emits shutdown_initiated metric

        Args:
            reason: Human-readable reason for shutdown (e.g., "signal 15",
                "Lock lost", "DQ threshold exceeded").

        Note:
            Idempotent - multiple calls have no additional effect.
            First call sets the reason, subsequent calls are ignored.
        """
        await asyncio.sleep(0)
        if self._requested:
            return  # Already shutting down, ignore

        self._requested = True
        self._reason = self._parse_reason(reason)
        self._reason_detail = reason
        self._event.set()

        self.logger.warning(
            "Shutdown initiated",
            reason=reason,
            reason_type=self._reason.value,
        )

        if self.metrics is not None:
            self.metrics.increment_counter(
                "bioetl_shutdown_initiated",
                value=1,
                labels={"reason": self._reason.value},
            )

    def request(self) -> None:
        """Synchronous shutdown request (backward compatibility).

        Use initiate_shutdown() for async contexts with reason tracking.
        This method exists for compatibility with existing ShutdownSignal
        usage patterns.

        Note:
            Does not emit metrics or log detailed reason.
        """
        if not self._requested:
            self._requested = True
            self._reason = ShutdownReason.UNKNOWN
            self._event.set()

    async def wait(self) -> None:
        """Wait until shutdown is requested.

        Blocks until initiate_shutdown() or request() is called.
        Use with asyncio.wait_for() for timeout-based waiting.

        This is backward-compatible with ShutdownSignal.wait().
        """
        await self._event.wait()

    async def wait_for_completion(self, timeout: float) -> bool:
        """Wait for shutdown completion with timeout.

        Blocks until mark_completed() is called or timeout expires.

        Args:
            timeout: Maximum seconds to wait for completion.

        Returns:
            True if shutdown completed within timeout, False if timeout expired.
        """
        try:
            async with asyncio.timeout(timeout):
                await self._completion_event.wait()
            return True
        except TimeoutError:
            self.logger.warning(
                "Shutdown completion timeout",
                timeout_seconds=timeout,
            )
            return False

    def mark_completed(self) -> None:
        """Mark shutdown as completed.

        Called by the runner after all cleanup is done.
        Signals wait_for_completion() to return.
        """
        self._completion_event.set()

        if self.metrics is not None:
            self.metrics.increment_counter(
                "bioetl_shutdown_completed",
                value=1,
                labels={"reason": self._reason.value},
            )

    def reset(self) -> None:
        """Reset service for reuse (e.g., in tests).

        Warning: Only use in tests or when you're certain no components
        are currently checking the shutdown state.
        """
        self._requested = False
        self._event.clear()
        self._completion_event.clear()
        self._reason = ShutdownReason.UNKNOWN
        self._reason_detail = ""

    @staticmethod
    def _parse_reason(reason: str) -> ShutdownReason:
        """Parse reason string to ShutdownReason enum.

        Args:
            reason: Human-readable shutdown reason.

        Returns:
            Matching ShutdownReason, or UNKNOWN if not recognized.
        """
        reason_lower = reason.lower()

        # Pattern matching table: (keywords, result)
        patterns: list[tuple[tuple[str, ...], ShutdownReason]] = [
            (("sigterm", "signal 15"), ShutdownReason.SIGNAL_SIGTERM),
            (("sigint", "signal 2"), ShutdownReason.SIGNAL_SIGINT),
            (("timeout",), ShutdownReason.TIMEOUT),
            (("user",), ShutdownReason.USER_REQUESTED),
        ]

        for keywords, result in patterns:
            if any(kw in reason_lower for kw in keywords):
                return result

        # Special case: requires both "lock" and "lost"
        if "lock" in reason_lower and "lost" in reason_lower:
            return ShutdownReason.LOCK_LOST

        # DQ threshold check
        if "dq" in reason_lower or "threshold" in reason_lower:
            return ShutdownReason.DQ_THRESHOLD_EXCEEDED

        return ShutdownReason.UNKNOWN


__all__ = [
    "PipelineShutdownError",
    "ShutdownReason",
    "ShutdownService",
]
