"""CrossRef-specific exceptions.

These exceptions are internal to the CrossRef adapter and should be
translated to domain-level ExternalServiceError on adapter boundary.

Application layer should catch ExternalServiceError, not these exceptions.
"""

from __future__ import annotations

from bioetl.domain.exceptions import ExternalServiceError
from bioetl.domain.types import ErrorType


class CrossRefApiError(ExternalServiceError):
    """CrossRef API error.

    Internal exception for CrossRef adapter. On adapter boundary, this
    should be translated to domain ExternalServiceError or its subclasses.
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        doi: str | None = None,
        operation: str | None = None,
    ) -> None:
        """Initialize CrossRefApiError.

        Args:
            message: Error description.
            status_code: HTTP status code if applicable.
            doi: DOI being fetched if applicable.
            operation: Operation that failed (e.g., "fetch", "search").
        """
        self.doi = doi
        self.operation = operation
        super().__init__(
            message,
            service_name="crossref",
            status_code=status_code,
        )


__all__ = [
    "CrossRefApiError",
]
