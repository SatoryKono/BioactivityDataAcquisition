"""No-operation logger implementation.

Provides a null object pattern implementation for logging when
logging is not configured or not needed (e.g., in adapters without
explicit logger injection).

This implementation is in infrastructure layer (not domain) because
it's a concrete implementation detail, even though it does nothing.
"""

from __future__ import annotations

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

    def bind(self, **_kwargs: Any) -> Self:
        """Bind additional context (no-op, returns self)."""
        return self

    def info(
        self, _event: str | None = None, *_args: Any, **_kwargs: Any
    ) -> None:
        """Log info message (no-op)."""
        pass

    def warning(
        self, _event: str | None = None, *_args: Any, **_kwargs: Any
    ) -> None:
        """Log warning message (no-op)."""
        pass

    def error(
        self, _event: str | None = None, *_args: Any, **_kwargs: Any
    ) -> None:
        """Log error message (no-op)."""
        pass

    def debug(
        self, _event: str | None = None, *_args: Any, **_kwargs: Any
    ) -> None:
        """Log debug message (no-op)."""
        pass

    def exception(
        self, _event: str | None = None, *_args: Any, **_kwargs: Any
    ) -> None:
        """Log exception with traceback (no-op)."""
        pass
