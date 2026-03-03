"""Structured logging implementation for BioETL.

Implements RULES.md §3.2 - Log Schema with mandatory fields:
- ts: ISO timestamp
- level: log level
- run_id: correlation ID (UUID)
- pipeline: pipeline name
- stage: extract | transform | load
- dataset: logical table name (SHOULD)
- record_count: count of records (SHOULD)

Requirements:
- REQ-OBS-001: run_id mandatory in all logs
- REQ-OBS-004: Structured JSON format
- REQ-OBS-005: Log Schema with mandatory fields
"""

from __future__ import annotations

from typing import Any, Self
from uuid import UUID

import structlog

from bioetl.infrastructure.observability.logging_config import configure_logging


def create_logger(
    pipeline: str,
    run_id: str | UUID,
    *,
    log_level: str = "INFO",
    json_format: bool = True,
) -> StructlogLogger:
    """Create a StructlogLogger with bound pipeline and run_id context.

    Args:
        pipeline: Pipeline name for log context.
        run_id: Unique run identifier for tracing.
        log_level: Logging level (default: INFO).
        json_format: Use JSON output format (default: True).

    Returns:
        Configured StructlogLogger instance.
    """
    configure_logging(json_format=json_format, log_level=log_level)
    base = structlog.get_logger(f"bioetl.{pipeline}")
    bound = base.bind(run_id=str(run_id), pipeline=pipeline)
    return StructlogLogger(bound)


class StructlogLogger:
    """Formal LoggerPort adapter wrapping structlog.

    This adapter provides a formal implementation of LoggerPort,
    replacing duck typing with explicit interface implementation.

    The class wraps structlog.stdlib.BoundLogger and ensures
    type-safe integration with the domain layer.

    Example:
        >>> logger = StructlogLogger(structlog.get_logger())
        >>> logger.info("event_name", key="value")
        >>> bound = logger.bind(run_id="123")
        >>> bound.warning("another_event")
    """

    __slots__ = ("_logger",)

    def __init__(self, logger: structlog.stdlib.BoundLogger) -> None:
        """Initialize with a structlog BoundLogger.

        Args:
            logger: The underlying structlog logger instance.
        """
        self._logger = logger

    def bind(self, **kwargs: Any) -> Self:  # Any: structlog-compatible API
        """Bind additional context to the logger.

        Returns a new StructlogLogger instance with the bound context.

        Args:
            **kwargs: Key-value pairs to bind to the logger context.

        Returns:
            New StructlogLogger with bound context.
        """
        bound = self._logger.bind(**kwargs)
        return self.__class__(bound)

    def info(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        """Log an informational message.

        Args:
            _event: The event name/message.
            **kwargs: Additional context for the log entry.

        Returns:
            The Any result.
        """
        return self._logger.info(_event, **kwargs)

    # Any: structlog-compatible API
    def warning(self, _event: str, **kwargs: Any) -> Any:
        """Log a warning message.

        Args:
            _event: The event name/message.
            **kwargs: Additional context for the log entry.

        Returns:
            The Any result.
        """
        return self._logger.warning(_event, **kwargs)

    # Any: structlog-compatible API
    def error(self, _event: str, **kwargs: Any) -> Any:
        """Log an error message.

        Args:
            _event: The event name/message.
            **kwargs: Additional context for the log entry.

        Returns:
            The Any result.
        """
        return self._logger.error(_event, **kwargs)

    # Any: structlog-compatible API
    def debug(self, _event: str, **kwargs: Any) -> Any:
        """Log a debug message.

        Args:
            _event: The event name/message.
            **kwargs: Additional context for the log entry.

        Returns:
            The Any result.
        """
        return self._logger.debug(_event, **kwargs)

    # Any: structlog-compatible API
    def exception(self, _event: str, **kwargs: Any) -> Any:
        """Log an exception with traceback.

        Args:
            _event: The event name/message.
            **kwargs: Additional context for the log entry.

        Returns:
            The Any result.
        """
        return self._logger.exception(_event, **kwargs)
