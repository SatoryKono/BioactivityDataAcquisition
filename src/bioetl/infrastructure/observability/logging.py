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

import logging
import sys
from typing import Any, Self
from uuid import UUID

import structlog

from bioetl.domain.ports import LoggerPort


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

    def bind(self, **kwargs: Any) -> Self:
        """Bind additional context to the logger.

        Returns a new StructlogLogger instance with the bound context.

        Args:
            **kwargs: Key-value pairs to bind to the logger context.

        Returns:
            New StructlogLogger with bound context.
        """
        bound = self._logger.bind(**kwargs)
        return self.__class__(bound)

    def info(self, _event: str, **kwargs: Any) -> Any:
        """Log an informational message.

        Args:
            _event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        return self._logger.info(_event, **kwargs)

    def warning(self, _event: str, **kwargs: Any) -> Any:
        """Log a warning message.

        Args:
            _event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        return self._logger.warning(_event, **kwargs)

    def error(self, _event: str, **kwargs: Any) -> Any:
        """Log an error message.

        Args:
            _event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        return self._logger.error(_event, **kwargs)

    def debug(self, _event: str, **kwargs: Any) -> Any:
        """Log a debug message.

        Args:
            _event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        return self._logger.debug(_event, **kwargs)

    def exception(self, _event: str, **kwargs: Any) -> Any:
        """Log an exception with traceback.

        Args:
            _event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        return self._logger.exception(_event, **kwargs)


def create_logger(
    pipeline: str,
    run_id: UUID,
    log_level: str = "INFO",
    json_format: bool = True,
) -> LoggerPort:
    """Create a structured logger factory.

    Args:
        pipeline: Pipeline name for log context.
        run_id: Unique run identifier for tracing.
        log_level: Logging level (default: INFO).
        json_format: Use JSON output format (default: True).

    Returns:
        StructlogLogger implementing LoggerPort with bound context.

    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger(f"bioetl.{pipeline}")
    bound_logger = logger.bind(run_id=str(run_id), pipeline=pipeline)

    # Set the log level for the underlying standard logger
    logging.basicConfig(
        level=log_level.upper(),
        stream=sys.stdout,
        format="%(message)s",
    )

    return StructlogLogger(bound_logger)
