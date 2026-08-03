"""Logger protocol port."""

from __future__ import annotations

from typing import Any, Protocol, Self, runtime_checkable


@runtime_checkable
class LoggerPort(Protocol):
    """Port for structured logging."""

    def bind(self, **kwargs: Any) -> Self:  # Any: structlog-compatible API
        """Return a new logger with additional bound context key-value pairs.

        Args:
            **kwargs: Key-value pairs to bind to the logger context.

        Returns:
            New logger instance with the provided context bound.
        """
        ...

    def info(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        """Emit an informational log event.

        Args:
            _event: Log event message string.
            **kwargs: Additional structured context fields.

        Returns:
            Implementation-defined return value (structlog-compatible).
        """
        ...

    def warning(
        self,
        _event: str,
        **kwargs: Any,  # Any: structlog-compatible API
    ) -> Any:  # Any: structlog-compatible API
        """Emit a warning log event.

        Args:
            _event: Log event message string.
            **kwargs: Additional structured context fields.

        Returns:
            Implementation-defined return value (structlog-compatible).
        """
        ...

    def error(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        """Emit an error log event.

        Args:
            _event: Log event message string.
            **kwargs: Additional structured context fields.

        Returns:
            Implementation-defined return value (structlog-compatible).
        """
        ...

    def debug(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible API
        """Emit a debug log event.

        Args:
            _event: Log event message string.
            **kwargs: Additional structured context fields.

        Returns:
            Implementation-defined return value (structlog-compatible).
        """
        ...

    def exception(
        self,
        _event: str,
        **kwargs: Any,  # Any: structlog-compatible API
    ) -> Any:  # Any: structlog-compatible API
        """Emit an error log event with current exception information attached.

        Args:
            _event: Log event message string.
            **kwargs: Additional structured context fields.

        Returns:
            Implementation-defined return value (structlog-compatible).
        """
        ...
