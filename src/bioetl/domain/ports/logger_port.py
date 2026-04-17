"""Logger port interface for BioETL.

This module defines the LoggerPort protocol that provides a structured
logging interface for the application. All logging implementations
should conform to this interface.

REQ-OBS-001: Logging should be structured and consistent
REQ-OBS-002: Logs should include contextual information
"""

from __future__ import annotations

from typing import Any, Protocol


class LoggerPort(Protocol):
    """Logger port protocol for structured logging.

    This protocol defines the logging interface that should be implemented
    by all logging adapters in the infrastructure layer.
    """

    def error(self, message: str, **kwargs: Any) -> None:  # Any: Generic context data for structured logging
        """Log an error message with context.

        Args:
            message: The error message
            **kwargs: Additional context data for structured logging
        """
        ...

    def warning(self, message: str, **kwargs: Any) -> None:  # Any: Generic context data for structured logging
        """Log a warning message with context.

        Args:
            message: The warning message
            **kwargs: Additional context data for structured logging
        """
        ...

    def info(self, message: str, **kwargs: Any) -> None:  # Any: Generic context data for structured logging
        """Log an informational message with context.

        Args:
            message: The informational message
            **kwargs: Additional context data for structured logging
        """
        ...

    def debug(self, message: str, **kwargs: Any) -> None:  # Any: Generic context data for structured logging
        """Log a debug message with context.

        Args:
            message: The debug message
            **kwargs: Additional context data for structured logging
        """
        ...
