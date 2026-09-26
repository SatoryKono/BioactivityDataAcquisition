"""Base infrastructure exceptions."""

from __future__ import annotations

from bioetl.domain.exceptions.base import CriticalError
from bioetl.domain.types import ErrorType


class InfrastructureError(CriticalError):
    """Base class for infrastructure-related errors."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(
        self,
        message: str,
        failed_components: list[str] | None = None,
    ) -> None:
        self.failed_components = failed_components or []
        super().__init__(message)
