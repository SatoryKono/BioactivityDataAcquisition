"""
HTTP error handler abstractions and implementations.

Provides unified error classification and handling for HTTP responses.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from bioetl.domain.errors import ClientRateLimitError
from bioetl.domain.observability import LoggingPortABC
from bioetl.infrastructure.errors import ApiClientError, ApiUnexpectedStatusError


class ErrorCategory(Enum):
    """Categories of HTTP errors for classification."""

    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    SUCCESS = "success"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RequestContext:
    """Context information for an HTTP request."""

    provider: str
    endpoint: str
    status_code: int | None
    method: str = "GET"
    response_body: str | None = None


class HttpErrorHandlerABC(ABC):
    """
    Abstract base class for HTTP error handling.

    Provides unified interface for classifying and handling HTTP errors
    across different client implementations.
    """

    @abstractmethod
    def handle(self, response: Any, context: RequestContext) -> ApiClientError | None:
        """
        Handle HTTP response and return appropriate error if needed.

        Args:
            response: HTTP response object
            context: Request context with provider, endpoint, status_code

        Returns:
            ApiClientError subclass if error detected, None if successful response
        """
        ...

    @abstractmethod
    def classify_error(self, status_code: int) -> ErrorCategory:
        """
        Classify HTTP status code into error category.

        Args:
            status_code: HTTP status code

        Returns:
            ErrorCategory enum value
        """
        ...


class DefaultHttpErrorHandler(HttpErrorHandlerABC):
    """
    Default implementation of HTTP error handler.

    Classification logic:
    - 429 → RateLimitError
    - 5xx → RetryableServerError (as ApiUnexpectedStatusError)
    - 4xx → ClientError with details
    - 2xx/3xx → Success (no error)
    """

    def __init__(self, logger: LoggingPortABC | None = None) -> None:
        """
        Initialize error handler.

        Args:
            logger: Optional logger for error details
        """
        self.logger = logger

    def handle(self, response: Any, context: RequestContext) -> ApiClientError | None:
        """
        Handle HTTP response and return appropriate error if needed.

        Args:
            response: HTTP response object (expected to have status_code attribute)
            context: Request context

        Returns:
            ApiClientError subclass if error, None otherwise
        """
        status_code = context.status_code
        if status_code is None:
            raw_status = getattr(response, "status_code", None)
            status_code = raw_status if isinstance(raw_status, int) else None

        if status_code is None:
            return None

        category = self.classify_error(status_code)

        if category == ErrorCategory.SUCCESS:
            return None

        if category == ErrorCategory.RATE_LIMIT:
            return self._create_rate_limit_error(context)

        if category == ErrorCategory.SERVER_ERROR:
            return self._create_server_error(context)

        if category == ErrorCategory.CLIENT_ERROR:
            return self._create_client_error(context)

        return self._create_generic_error(context)

    def classify_error(self, status_code: int) -> ErrorCategory:
        """
        Classify HTTP status code into error category.

        Args:
            status_code: HTTP status code

        Returns:
            ErrorCategory enum value
        """
        if 200 <= status_code < 400:
            return ErrorCategory.SUCCESS

        if status_code == 429:
            return ErrorCategory.RATE_LIMIT

        if 500 <= status_code < 600:
            return ErrorCategory.SERVER_ERROR

        if 400 <= status_code < 500:
            return ErrorCategory.CLIENT_ERROR

        return ErrorCategory.UNKNOWN

    def _create_rate_limit_error(self, context: RequestContext) -> ClientRateLimitError:
        """Create rate limit error."""
        self._log_error("rate_limit_error", context)
        return ClientRateLimitError(
            provider=context.provider,
            message=f"Rate limit exceeded (HTTP {context.status_code})",
            endpoint=context.endpoint,
            status_code=context.status_code,
        )

    def _create_server_error(self, context: RequestContext) -> ApiUnexpectedStatusError:
        """Create server error (5xx)."""
        self._log_error("server_error", context)
        return ApiUnexpectedStatusError(
            f"Server error: {context.status_code}",
            provider=context.provider,
            endpoint=context.endpoint,
            status_code=context.status_code,
        )

    def _create_client_error(self, context: RequestContext) -> ApiUnexpectedStatusError:
        """Create client error (4xx)."""
        self._log_error("client_error", context)
        detail = self._get_client_error_detail(context.status_code)
        return ApiUnexpectedStatusError(
            f"Client error ({detail}): {context.status_code}",
            provider=context.provider,
            endpoint=context.endpoint,
            status_code=context.status_code,
        )

    def _create_generic_error(self, context: RequestContext) -> ApiClientError:
        """Create generic error for unknown status codes."""
        self._log_error("unknown_error", context)
        return ApiClientError(
            f"Unexpected status code: {context.status_code}",
            provider=context.provider,
            endpoint=context.endpoint,
            status_code=context.status_code,
        )

    def _get_client_error_detail(self, status_code: int | None) -> str:
        """Get human-readable detail for client error status codes."""
        details = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            406: "Not Acceptable",
            408: "Request Timeout",
            409: "Conflict",
            410: "Gone",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
        }
        return details.get(status_code or 0, "Unknown Client Error")

    def _log_error(self, event: str, context: RequestContext) -> None:
        """Log error details if logger is available."""
        if self.logger is None:
            return

        self.logger.error(
            event,
            provider=context.provider,
            endpoint=context.endpoint,
            status_code=context.status_code,
            method=context.method,
        )
