"""Port for adapter-facing error handling workflows."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.exceptions import ExternalServiceError
from bioetl.domain.types import ErrorType, JsonDict

__all__ = ["ErrorHandlerPort"]


@runtime_checkable
class ErrorHandlerPort(Protocol):
    """Classify, log, and wrap provider errors into domain exceptions."""

    def get_error_type(self, error: Exception) -> ErrorType:
        """Return normalized domain error type for ``error``."""
        ...

    def log_error(
        self,
        provider: str,
        operation: str,
        error: Exception,
        context: JsonDict | None = None,  # Any: untyped API JSON record
    ) -> object:
        """Emit structured error log and return provider-specific context object."""
        ...

    def wrap_error(
        self,
        error: Exception,
        provider: str,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> ExternalServiceError:
        """Wrap low-level exception into domain ``ExternalServiceError``."""
        ...

    def handle_error(
        self,
        error: Exception,
        provider: str,
        operation: str,
        context: JsonDict | None = None,  # Any: untyped API JSON record
    ) -> ExternalServiceError:
        """Log and wrap error in one step (convenience composition of log+wrap)."""
        ...
