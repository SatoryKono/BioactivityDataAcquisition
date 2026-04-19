"""Logging helpers module for common logging operations."""

from __future__ import annotations

from logging import Logger


def log_error(logger: Logger, error: str) -> None:
    """Log an error message.

    Args:
        logger: Logger instance.
        error: Error message to log.
    """
    logger.error(f"Error occurred: {error}")


def log_debug(logger: Logger, details: str) -> None:
    """Log a debug message.

    Args:
        logger: Logger instance.
        details: Debug details to log.
    """
    logger.debug(f"Debug info: {details}")
