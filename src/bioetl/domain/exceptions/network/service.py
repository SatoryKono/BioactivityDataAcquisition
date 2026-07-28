# pyright: reportAttributeAccessIssue=false
# Host attrs/methods provided by concrete composition.
"""External service network exceptions.

Covers errors returned by external APIs and services (HTTP 4xx/5xx),
rate limiting, authentication failures, and data validation errors.

These exceptions provide abstract error types for external data sources.
Domain/application layers should catch these abstract exceptions, not
provider-specific ones. Infrastructure adapters MUST translate provider-specific
errors into this hierarchy at the adapter boundary (RULES.md §7.2).

All exceptions inherit from RecoverableError, indicating that
retry with exponential backoff is appropriate (per RULES.md §3.1.3).
"""

from __future__ import annotations

from typing import cast

from bioetl.domain.exceptions.base import RecoverableError
from bioetl.domain.exceptions.network_rate_limit_helpers import (
    resolve_rate_limit_params as _resolve_rate_limit_params,
)
from bioetl.domain.types import ErrorType

__all__ = [
    "ApiError",
    "DataValidationError",
    "ExternalServiceError",
    "RateLimitError",
    "RateLimitExceededError",
    "ServiceAuthenticationError",
    "ServiceUnavailableError",
]


class ApiError(RecoverableError):
    """Raised when external API returns an error.

    This is a generic API error that may be retryable depending on the status code.
    For more specific external service errors, see ExternalServiceError hierarchy.

    Attributes:
        message: Error message from the API.
        status_code: Optional HTTP status code.

    Example:
        >>> raise ApiError("Invalid request parameters", status_code=400)
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize ApiError.

        Args:
            message: Error message from the API.
            status_code: Optional HTTP status code.
        """
        self.message = message
        self.status_code = status_code
        msg = message
        if status_code:
            msg = f"[{status_code}] {message}"
        super().__init__(msg)


# =============================================================================
# External Service Exceptions (RULES.md §7.2)
# =============================================================================
#
# These exceptions provide abstract error types for external data sources.
# Domain/application layers should catch these abstract exceptions, not
# provider-specific ones. Infrastructure adapters MUST translate provider-specific
# errors into this hierarchy at the adapter boundary.


class ExternalServiceError(RecoverableError):
    """Base exception for all external service errors.

    This is the abstract exception that domain/application layers should catch
    when handling errors from external data sources.

    Infrastructure adapters MUST translate provider-specific errors into this
    hierarchy on the adapter boundary.

    Attributes:
        service_name: Optional name of the service that failed.
        status_code: Optional HTTP status code if applicable.
        retry_after: Optional seconds to wait before retry.

    Example:
        >>> try:
        ...     await adapter.fetch("entity")
        ... except ExternalServiceError as e:
        ...     logger.error("External service failed", service=e.service_name)
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        """Initialize ExternalServiceError.

        Args:
            message: Error description.
            service_name: Name of the external service (e.g., "chembl", "crossref").
            status_code: HTTP status code if applicable.
            retry_after: Seconds to wait before retry if applicable.
        """
        self.service_name = service_name
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(message)


class ServiceUnavailableError(ExternalServiceError):
    """Raised when external service is unavailable.

    Typically caused by:
    - HTTP 5xx errors (500, 502, 503, 504)
    - Connection timeouts
    - DNS resolution failures

    The request may be retried after exponential backoff.

    Example:
        >>> raise ServiceUnavailableError(
        ...     "ChEMBL API returned 503",
        ...     service_name="chembl",
        ...     status_code=503,
        ...     retry_after=60.0
        ... )
    """

    error_type = ErrorType.TIMEOUT

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        """Initialize ServiceUnavailableError.

        Args:
            message: Error description.
            service_name: Name of the unavailable service.
            status_code: HTTP status code (typically 5xx).
            retry_after: Seconds to wait before retry.
        """
        super().__init__(
            message,
            service_name=service_name,
            status_code=status_code,
            retry_after=retry_after,
        )


class RateLimitError(ExternalServiceError):
    """Raised when provider-side rate limit is exceeded."""

    error_type = ErrorType.RATE_LIMIT

    def __init__(
        self,
        provider: str | None = None,
        retry_after: float = 60.0,
        *,
        message: str | None = None,
        service_name: str | None = None,
    ) -> None:
        """Initialize unified RateLimitError."""
        if message is None and service_name is None:
            if provider is None:
                raise ValueError("provider is required for RateLimitError")
            self.provider = provider
            self.retry_after = retry_after
            RecoverableError.__init__(
                self,
                f"Rate limit exceeded for {provider}. Retry after {retry_after}s",
            )
            return

        provider_name, resolved_message, resolved_service = _resolve_rate_limit_params(
            provider,
            message,
            service_name,
        )
        self.provider = provider_name
        super().__init__(
            resolved_message,
            service_name=resolved_service,
            status_code=429,
            retry_after=retry_after,
        )


RateLimitExceededError = RateLimitError


class ServiceAuthenticationError(ExternalServiceError):
    """Raised when external service authentication fails.

    Caused by HTTP 401 Unauthorized or 403 Forbidden.

    Note:
        This is a RECOVERABLE error in the external service hierarchy
        because it may be caused by expired tokens that can be refreshed.
        For truly critical auth failures, see AuthFailureError in internal module.

    Example:
        >>> raise ServiceAuthenticationError(
        ...     "UniProt API key expired",
        ...     service_name="uniprot",
        ...     status_code=401
        ... )
    """

    error_type = ErrorType.AUTH_FAILURE

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """Initialize ServiceAuthenticationError.

        Args:
            message: Error description.
            service_name: Name of the service that rejected auth.
            status_code: HTTP status code (401 or 403).
        """
        super().__init__(
            message,
            service_name=service_name,
            status_code=status_code,
        )


def data_validation_error(
    message: str,
    service_name: str | None = None,
    field: str | None = None,
    value: str | None = None,
) -> ExternalServiceError:
    """Compatibility constructor for legacy DataValidationError.

    Args:
        message: Human-readable description of the validation failure.
        service_name: Optional name of the external service that returned invalid data;
            defaults to None.
        field: Optional field name that failed validation; defaults to None.
        value: Optional string representation of the invalid value; defaults to None.

    Returns:
        ExternalServiceError with INVALID_DATA type and field/value context attached.
    """
    error = ExternalServiceError(message, service_name=service_name)
    error = cast(
        ExternalServiceError,
        error.with_context(
            field=field,
            value=value,
        ),
    )
    error.error_type = ErrorType.INVALID_DATA  # type: ignore[misc]  # instance override of ClassVar
    return error


DataValidationError = data_validation_error
