"""Port for deterministic exception-to-error-type classification."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.types import ErrorType

__all__ = ["ErrorClassifierPort"]


@runtime_checkable
class ErrorClassifierPort(Protocol):
    """Classify exceptions into domain ``ErrorType`` values."""

    def classify(self, error: Exception) -> ErrorType:
        """Return normalized error type for ``error``.

        Args:
            error: Exception to classify into a domain ErrorType.

        Returns:
            Normalized ErrorType value for the exception.
        """
        ...
