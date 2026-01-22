"""Observability-related exceptions.

Contains exceptions for metrics server operations that need to be shared
across layers (infrastructure, application, interfaces).

Following the pattern from infrastructure/adapters/{provider}/exceptions.py,
these exceptions are defined in infrastructure but can be safely imported
by higher layers (application, interfaces) since exceptions are value objects.
"""

from __future__ import annotations


class MetricsServerError(Exception):
    """Raised when metrics server fails to start with fail_fast=True.

    This exception is raised by the Prometheus metrics server when it cannot
    bind to the specified port and fail_fast mode is enabled.

    Attributes:
        port: Port that failed to bind.
        reason: Reason for failure (e.g., "port_in_use", "os_error", "unexpected").
        original_error: Underlying exception that caused the failure.
    """

    def __init__(
        self, port: int, reason: str, original_error: Exception | None = None
    ) -> None:
        """Initialize MetricsServerError.

        Args:
            port: Port that failed.
            reason: Reason for failure.
            original_error: Underlying exception.
        """
        super().__init__(f"Failed to start metrics server on port {port}: {reason}")
        self.port = port
        self.reason = reason
        self.original_error = original_error


__all__ = ["MetricsServerError"]
