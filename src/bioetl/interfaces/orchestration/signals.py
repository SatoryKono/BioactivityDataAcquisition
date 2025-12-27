"""OS Signal Handling for Graceful Shutdown.

This module provides a concrete implementation for listening to OS signals
(SIGTERM, SIGINT) and translating them into an application-level
ShutdownSignal request.
"""

from __future__ import annotations

import signal
from typing import TYPE_CHECKING, Any

from bioetl.application.core.shutdown import ShutdownSignal

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def setup_shutdown_handlers(
    shutdown_signal: ShutdownSignal,
    logger: LoggerPort | None = None,
) -> None:
    """Setup signal handlers to trigger the application's shutdown signal.

    Args:
        shutdown_signal: The application's shared shutdown signal instance.
        logger: Logger port for logging signal events. If None, signals are
            handled silently (useful for testing).
    """

    def signal_handler(signum: int, _: Any) -> None:
        """Handle OS termination signals for graceful shutdown.

        This callback is registered with signal.signal() for SIGTERM and SIGINT.
        When triggered, it logs the signal (if logger available) and requests
        application shutdown via the ShutdownSignal instance.

        Args:
            signum: The signal number received (e.g., SIGTERM=15, SIGINT=2).
            _: Stack frame (unused, required by signal handler signature).

        Note:
            Logger is optional to support testing scenarios where logging
            infrastructure may not be available. See ADR-008 for graceful
            shutdown strategy details.
        """
        if logger is not None:
            logger.warning(
                "Received signal, initiating graceful shutdown",
                signal_name=signal.strsignal(signum),
                signal_num=signum,
            )
        shutdown_signal.request()

    try:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    except ValueError:
        # This can happen if not in the main thread
        if logger is not None:
            logger.warning("Cannot set signal handlers in a non-main thread")
