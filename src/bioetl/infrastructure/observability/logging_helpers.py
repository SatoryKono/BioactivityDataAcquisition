"""Logging helpers module for common logging operations."""

from __future__ import annotations

from bioetl.domain.ports import LoggerPort


def log_error(logger: LoggerPort, error: str) -> None:
    """Log an error message through the structured observability port.

    Args:
        logger: LoggerPort instance.
        error: Error message to log.
    """
    logger.error("error_occurred", error=error)


def log_debug(logger: LoggerPort, details: str) -> None:
    """Log a debug message through the structured observability port.

    Args:
        logger: LoggerPort instance.
        details: Debug details to log.
    """
    logger.debug("debug_info", details=details)
