"""OS Signal Handling for Graceful Shutdown.

Minimal interfaces layer: registers OS signals and delegates to ShutdownPort.
See ADR-008 for graceful shutdown strategy details.
"""

from __future__ import annotations

import asyncio
import signal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from asyncio import Task

    from bioetl.domain.ports import LoggerPort, ShutdownPort

# Module-level storage for background tasks to prevent garbage collection
_background_tasks: set[Task[None]] = set()


def register_signal_handlers(
    shutdown_service: ShutdownPort,
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
