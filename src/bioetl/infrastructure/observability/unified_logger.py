"""Unified structured logging with enforced Log Schema.

Implements RULES.md §3.2.1 - Log Schema with mandatory fields:
- timestamp: ISO timestamp (automatic via structlog)
- level: log level (from method call)
- run_id: correlation ID (MUST be provided at initialization)
- pipeline: pipeline name (MUST be provided at initialization)
- stage: extract | transform | load (defaults to "init" if not provided)

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

__all__ = ["StageType", "UnifiedLogger", "create_unified_logger"]

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, Self

import structlog

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.observability.logging_config import configure_logging

if TYPE_CHECKING:
    from uuid import UUID

# Stage values allowed by Log Schema
StageType = Literal["extract", "transform", "load", "validate", "init", "cleanup"]

# Default stage when not provided (for LoggerPort compatibility)
_DEFAULT_STAGE: StageType = "init"
_EVENT_KWARG: str = "event"
_EXTRA_KWARG: str = "extra"


class UnifiedLogger:
    """Unified logger with enforced Log Schema fields.

    This logger enforces the mandatory fields defined in RULES.md §3.2.1:
    - run_id and pipeline are bound at initialization
    - stage defaults to "init" if not provided (for LoggerPort compatibility)

    The logger also includes secret filtering to prevent accidental
    logging of sensitive data like API keys, tokens, and passwords.

    Implements LoggerPort protocol with signature: method(_event: str, **kwargs: Any)
    Schema fields (stage, dataset, record_count, error_type) are extracted from kwargs.

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

    def bind(self, **kwargs: Any) -> Self:  # Any: structlog-compatible API
        """Bind additional context to the logger.

        Returns a new UnifiedLogger instance with additional bound context.
        The pipeline and run_id remain unchanged; any attempt to override them
        via kwargs is stripped so correlation fields stay immutable.

        Args:
            **kwargs: Key-value pairs to bind to the logger context

        Returns:
            New UnifiedLogger with bound context
        """
        safe_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key not in {"run_id", "pipeline"}
        }
        new_logger = object.__new__(self.__class__)
        new_logger._pipeline = self._pipeline
        new_logger._run_id = self._run_id
        new_logger._logger = self._logger.bind(**safe_kwargs)
        return new_logger

    def _strip_correlation_overrides(self, kwargs: dict[str, object]) -> dict[str, object]:
        """Drop run_id/pipeline overrides so bound correlation fields win."""
        return {
            key: value
            for key, value in kwargs.items()
            if key not in {"run_id", "pipeline"}
        }

    def _ensure_stage(
        self,
        kwargs: JsonDict,  # Any: structlog-compatible API
    ) -> JsonDict:  # Any: structlog-compatible API
        """Ensure stage field is present in kwargs.

        If stage is not provided, defaults to "init" for LoggerPort compatibility.

        Args:
            kwargs: Original keyword arguments

        Returns:
            kwargs with stage field ensured
        """
        if "stage" not in kwargs:
            kwargs["stage"] = _DEFAULT_STAGE
        return kwargs

    @staticmethod
    def _sanitize_kwargs(
        kwargs: JsonDict,  # Any: structlog-compatible API
    ) -> JsonDict:  # Any: structlog-compatible API
        """Normalize structured log kwargs into one flat schema.

        Returns:
            Dictionary with conflicting reserved keys removed and nested
            ``extra={...}`` context flattened into the top level.
        """
        sanitized = dict(kwargs)
        sanitized.pop(_EVENT_KWARG, None)
        extra_context = sanitized.pop(_EXTRA_KWARG, None)

        if isinstance(extra_context, Mapping):
            for key, value in extra_context.items():
                if key == _EVENT_KWARG or key in sanitized:
                    continue
                sanitized[key] = value
        elif extra_context is not None:
            sanitized[_EXTRA_KWARG] = extra_context

        return sanitized

    def info(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        """Log an informational message.

        Implements LoggerPort.info() with Log Schema enforcement.
        Stage defaults to "init" if not provided.

        Args:
            _event: The event message
            **kwargs: Additional context. Recognized schema fields:
                - stage: Pipeline stage (extract, transform, load, validate, init, cleanup)
                - dataset: Logical table name
                - record_count: Count of records

        Returns:
            The Any result.
        """
        context = self._ensure_stage(self._sanitize_kwargs(kwargs))
        return self._logger.info(_event, **context)

    def warning(
        self,
        _event: str,
        **kwargs: Any,  # Any: structlog/OTel-compatible API
    ) -> Any:  # Any: structlog-compatible API
        """Log a warning message.

        Implements LoggerPort.warning() with Log Schema enforcement.
        Stage defaults to "init" if not provided.

        Args:
            _event: The event message
            **kwargs: Additional context. Recognized schema fields:
                - stage: Pipeline stage
                - dataset: Logical table name

        Returns:
            The Any result.
        """
        context = self._ensure_stage(self._sanitize_kwargs(kwargs))
        return self._logger.warning(_event, **context)

    def error(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        """Log an error message.

        Implements LoggerPort.error() with Log Schema enforcement.
        Stage defaults to "init" if not provided.

        Args:
            _event: The event message
            **kwargs: Additional context. Recognized schema fields:
                - stage: Pipeline stage
                - error_type: Classification of the error
                - dataset: Logical table name

        Returns:
            The Any result.
        """
        context = self._ensure_stage(self._sanitize_kwargs(kwargs))
        return self._logger.error(_event, **context)

    def debug(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        """Log a debug message.

        Implements LoggerPort.debug() with Log Schema enforcement.
        Stage defaults to "init" if not provided.

        Args:
            _event: The event message
            **kwargs: Additional context

        Returns:
            The Any result.
        """
        context = self._ensure_stage(self._sanitize_kwargs(kwargs))
        return self._logger.debug(_event, **context)

    def exception(
        self,
        _event: str,
        **kwargs: Any,  # Any: structlog/OTel-compatible API
    ) -> Any:  # Any: structlog-compatible API
        """Log an exception with traceback.

        Implements LoggerPort.exception() with Log Schema enforcement.
        Stage defaults to "init" if not provided.

        Args:
            _event: The event message
            **kwargs: Additional context. Recognized schema fields:
                - stage: Pipeline stage
                - error_type: Classification of the error

        Returns:
            The Any result.
        """
        context = self._ensure_stage(self._sanitize_kwargs(kwargs))
        return self._logger.exception(_event, **context)


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
