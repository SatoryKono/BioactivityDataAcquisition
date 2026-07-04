"""No-operation logger implementation.

Provides a null object pattern implementation for logging when
logging is not configured or not needed (e.g., in adapters without
explicit logger injection).

This implementation is in infrastructure layer (not domain) because
it's a concrete implementation detail, even though it does nothing.
"""

from __future__ import annotations

__all__ = ["NoOpLogger"]


from typing import Any, Self


class NoOpLogger:
    """No-operation logger implementing LoggerPort.

    Used as a fallback when no logger is explicitly provided to adapters.
    All operations are silently ignored. This ensures adapters can safely
    call logging methods even when no logger is injected.

    Example:
        >>> # In adapter without logger
        >>> logger = NoOpLogger()
        >>> logger.info("This will be silently ignored")

        >>> # Bound context is also a no-op
        >>> bound_logger = logger.bind(run_id="123")
        >>> bound_logger.warning("Also ignored")

    """

    def bind(self, **_kwargs: Any) -> Self:  # Any: structlog-compatible API
        """Bind additional context (no-op, returns self).

        Args:
            **_kwargs: Additional keyword arguments.

        Returns:
            Logger with bound context.
        """
        return self

    # Any: structlog-compatible API
    def info(
        self,
        _event: str,
        **_kwargs: Any,  # Any: structlog/OTel-compatible API
    ) -> None:  # Any: structlog/OTel-compatible API
        """Log info message (no-op).

        Args:
            _event:  event.
            **_kwargs: Additional keyword arguments.
        """

    # Any: structlog-compatible API
    def warning(
        self,
        _event: str,
        **_kwargs: Any,  # Any: structlog/OTel-compatible API
    ) -> None:  # Any: structlog/OTel-compatible API
        """Log warning message (no-op).

        Args:
            _event:  event.
            **_kwargs: Additional keyword arguments.
        """

    # Any: structlog-compatible API
    def error(
        self,
        _event: str,
        **_kwargs: Any,  # Any: structlog/OTel-compatible API
    ) -> None:  # Any: structlog/OTel-compatible API
        """Log error message (no-op).

        Args:
            _event:  event.
            **_kwargs: Additional keyword arguments.
        """

    # Any: structlog-compatible API
    def debug(
        self,
        _event: str,
        **_kwargs: Any,  # Any: structlog/OTel-compatible API
    ) -> None:  # Any: structlog/OTel-compatible API
        """Log debug message (no-op).

        Args:
            _event:  event.
            **_kwargs: Additional keyword arguments.
        """

    # Any: structlog-compatible API
    def exception(
        self,
        _event: str,
        **_kwargs: Any,  # Any: structlog/OTel-compatible API
    ) -> None:  # Any: structlog/OTel-compatible API
        """Log exception with traceback (no-op).

        Args:
            _event:  event.
            **_kwargs: Additional keyword arguments.
        """
