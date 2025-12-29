"""OS Signal Handling for Graceful Shutdown.

Minimal interfaces layer: registers OS signals and delegates to ShutdownPort.
See ADR-008 for graceful shutdown strategy details.
"""

from __future__ import annotations

import asyncio
import signal
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from asyncio import Task

    from bioetl.domain.ports import LoggerPort

# Module-level storage for background tasks to prevent garbage collection
_background_tasks: set[Task[None]] = set()


@runtime_checkable
class _ShutdownSignalLike(Protocol):
    """Protocol for backward compatibility with ShutdownSignal."""

    def request(self) -> None: ...


@runtime_checkable
class _ShutdownServiceLike(Protocol):
    """Protocol for new ShutdownService."""

    async def initiate_shutdown(self, reason: str) -> None: ...


def register_signal_handlers(
    shutdown_service: _ShutdownServiceLike,
    logger: LoggerPort | None = None,
) -> None:
    """Register OS signal handlers for graceful shutdown.

    Args:
        shutdown_service: Service implementing ShutdownPort for shutdown coordination.
        logger: Optional logger for signal events.
    """

    def handler(signum: int, _: Any) -> None:
        reason = f"signal {signum} ({signal.strsignal(signum)})"
        task = asyncio.create_task(shutdown_service.initiate_shutdown(reason))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    try:
        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)
    except ValueError:
        if logger:
            logger.warning("Cannot set signal handlers outside main thread")


def setup_shutdown_handlers(
    shutdown_signal: _ShutdownSignalLike,
    logger: LoggerPort | None = None,
) -> None:
    """Setup signal handlers (backward-compatible).

    Deprecated: Use register_signal_handlers() with ShutdownService instead.

    Args:
        shutdown_signal: Legacy ShutdownSignal instance.
        logger: Optional logger for signal events.
    """

    def handler(signum: int, _: Any) -> None:
        if logger:
            logger.warning(
                "Received signal, initiating graceful shutdown",
                signal_name=signal.strsignal(signum),
                signal_num=signum,
            )
        shutdown_signal.request()

    try:
        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)
    except ValueError:
        if logger:
            logger.warning("Cannot set signal handlers outside main thread")
