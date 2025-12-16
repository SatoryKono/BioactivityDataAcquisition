"""OS Signal Handling for Graceful Shutdown.

This module provides a concrete implementation for listening to OS signals
(SIGTERM, SIGINT) and translating them into an application-level
ShutdownSignal request.
"""
import signal
from typing import Any

import structlog

from bioetl.application.core.shutdown import ShutdownSignal


def setup_shutdown_handlers(shutdown_signal: ShutdownSignal) -> None:
    """Setup signal handlers to trigger the application's shutdown signal.

    Args:
        shutdown_signal: The application's shared shutdown signal instance.
    """
    logger = structlog.get_logger("signal_handler")

    def signal_handler(signum: int, _: Any) -> None:
        logger.warning(
            f"Received signal {signal.strsignal(signum)}, initiating graceful shutdown"
        )
        shutdown_signal.request()

    try:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    except ValueError:
        # This can happen if not in the main thread
        logger.warning("Cannot set signal handlers in a non-main thread.")

