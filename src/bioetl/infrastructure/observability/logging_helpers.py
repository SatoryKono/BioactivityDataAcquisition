"""Logging helpers module for common logging operations."""

from __future__ import annotations

from logging import Logger
from typing import cast

from bioetl.domain.ports import LoggerPort


def log_error(logger: Logger | LoggerPort | object, error: str) -> None:
    """Log an error message.

    Args:
        logger: Logger instance.
        error: Error message to log.
    """
    if isinstance(logger, Logger):
        logger.error("Error occurred: %s", error)
        return
    cast(LoggerPort, logger).error(f"Error occurred: {error}")


def log_debug(logger: Logger | LoggerPort | object, details: str) -> None:
    """Log a debug message.

    Args:
        logger: Logger instance.
        details: Debug details to log.
    """
    if isinstance(logger, Logger):
        logger.debug("Debug info: %s", details)
        return
    cast(LoggerPort, logger).debug(f"Debug info: {details}")
