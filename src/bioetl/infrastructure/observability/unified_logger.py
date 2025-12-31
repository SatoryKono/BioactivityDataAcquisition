"""Unified structured logging with enforced Log Schema.

Implements RULES.md §3.2.1 - Log Schema with mandatory fields:
- ts: ISO timestamp (automatic via structlog)
- level: log level (from method call)
- run_id: correlation ID (MUST be provided at initialization)
- pipeline: pipeline name (MUST be provided at initialization)
- stage: extract | transform | load (MUST be provided on each call)

Optional fields:
- dataset: logical table name (SHOULD)
- record_count: count of records (SHOULD)
- error_type: error classification (for error logs)

Requirements:
- REQ-OBS-001: run_id mandatory in all logs
- REQ-OBS-004: Structured JSON format
- REQ-OBS-005: Log Schema with mandatory fields

Note:
    This module uses centralized logging configuration from logging_config.py.
    The configuration is applied automatically on first logger creation.
    For explicit control, call configure_logging() at application startup.

Example:
    >>> from bioetl.infrastructure.observability.logging_config import configure_logging
    >>> configure_logging(json_format=True)
    >>> logger = UnifiedLogger(pipeline="chembl_activity", run_id="abc-123")
    >>> logger.info("Fetching page", stage="extract", page=5)
    >>> logger.error("Validation failed", stage="transform", error_type="schema_error")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Self

import structlog

from bioetl.infrastructure.observability.logging_config import configure_logging

if TYPE_CHECKING:
    from uuid import UUID

# Stage values allowed by Log Schema
StageType = Literal["extract", "transform", "load", "validate", "init", "cleanup"]


class UnifiedLogger:
    """Unified logger with enforced Log Schema fields.

    This logger enforces the mandatory fields defined in RULES.md §3.2.1:
    - run_id and pipeline are bound at initialization
    - stage is required on every log call

    The logger also includes secret filtering to prevent accidental
    logging of sensitive data like API keys, tokens, and passwords.

    Note:
        Uses centralized logging configuration from logging_config.py.
        Configuration is applied automatically if not already done.

    Example:
        >>> logger = UnifiedLogger(pipeline="chembl_activity", run_id="abc-123")
        >>> logger.info("Fetching records", stage="extract", record_count=100)
        >>> logger.error("Parse failed", stage="transform", error_type="json_error")
    """

    __slots__ = ("_logger", "_pipeline", "_run_id")

    def __init__(
        self,
        pipeline: str,
        run_id: str | UUID,
        log_level: str = "INFO",
        json_format: bool = True,
    ) -> None:
        """Initialize UnifiedLogger with mandatory context.

        Args:
            pipeline: Pipeline name for log context (MUST be provided)
            run_id: Unique run identifier for tracing (MUST be provided)
            log_level: Logging level (default: INFO)
            json_format: Use JSON output format (default: True)
        """
        self._pipeline = pipeline
        self._run_id = str(run_id)

        # Use centralized configuration (no-op if already configured)
        configure_logging(json_format=json_format, log_level=log_level)

        # Create logger with mandatory bound context
        base_logger = structlog.get_logger(f"bioetl.{pipeline}")
        self._logger = base_logger.bind(
            run_id=self._run_id,
            pipeline=pipeline,
        )

    def bind(self, **kwargs: Any) -> Self:
        """Bind additional context to the logger.

        Returns a new UnifiedLogger instance with additional bound context.
        The pipeline and run_id remain unchanged.

        Args:
            **kwargs: Key-value pairs to bind to the logger context

        Returns:
            New UnifiedLogger with bound context
        """
        new_logger = object.__new__(self.__class__)
        new_logger._pipeline = self._pipeline
        new_logger._run_id = self._run_id
        new_logger._logger = self._logger.bind(**kwargs)
        return new_logger

    def info(
        self,
        message: str,
        *,
        stage: StageType,
        dataset: str | None = None,
        record_count: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """Log an informational message with mandatory stage.

        Args:
            message: The event message
            stage: Pipeline stage (extract, transform, load, validate, init, cleanup)
            dataset: Logical table name (SHOULD provide)
            record_count: Count of records (SHOULD provide)
            **kwargs: Additional context for the log entry
        """
        extra = {"stage": stage, **kwargs}
        if dataset is not None:
            extra["dataset"] = dataset
        if record_count is not None:
            extra["record_count"] = record_count

        return self._logger.info(message, **extra)

    def warning(
        self,
        message: str,
        *,
        stage: StageType,
        dataset: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Log a warning message with mandatory stage.

        Args:
            message: The event message
            stage: Pipeline stage
            dataset: Logical table name (SHOULD provide)
            **kwargs: Additional context for the log entry
        """
        extra = {"stage": stage, **kwargs}
        if dataset is not None:
            extra["dataset"] = dataset

        return self._logger.warning(message, **extra)

    def error(
        self,
        message: str,
        *,
        stage: StageType,
        error_type: str,
        dataset: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Log an error message with mandatory stage and error_type.

        Args:
            message: The event message
            stage: Pipeline stage
            error_type: Classification of the error (e.g., "network", "validation", "schema")
            dataset: Logical table name (SHOULD provide)
            **kwargs: Additional context for the log entry
        """
        extra = {"stage": stage, "error_type": error_type, **kwargs}
        if dataset is not None:
            extra["dataset"] = dataset

        return self._logger.error(message, **extra)

    def debug(
        self,
        message: str,
        *,
        stage: StageType,
        **kwargs: Any,
    ) -> Any:
        """Log a debug message with mandatory stage.

        Args:
            message: The event message
            stage: Pipeline stage
            **kwargs: Additional context for the log entry
        """
        return self._logger.debug(message, stage=stage, **kwargs)

    def exception(
        self,
        message: str,
        *,
        stage: StageType,
        error_type: str,
        **kwargs: Any,
    ) -> Any:
        """Log an exception with traceback.

        Args:
            message: The event message
            stage: Pipeline stage
            error_type: Classification of the error
            **kwargs: Additional context for the log entry
        """
        return self._logger.exception(
            message,
            stage=stage,
            error_type=error_type,
            **kwargs,
        )


def create_unified_logger(
    pipeline: str,
    run_id: str | UUID,
    log_level: str = "INFO",
    json_format: bool = True,
) -> UnifiedLogger:
    """Factory function to create a UnifiedLogger.

    Convenience function for creating a UnifiedLogger with the
    specified configuration.

    Args:
        pipeline: Pipeline name for log context
        run_id: Unique run identifier for tracing
        log_level: Logging level (default: INFO)
        json_format: Use JSON output format (default: True)

    Returns:
        Configured UnifiedLogger instance
    """
    return UnifiedLogger(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
        json_format=json_format,
    )
