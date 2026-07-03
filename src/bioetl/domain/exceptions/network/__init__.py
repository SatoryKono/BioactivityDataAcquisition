"""Network exceptions for connectivity and external service errors.

These errors are typically transient and may succeed on retry. They cover:
- Network connectivity issues (timeouts, connection errors)
- Rate limiting from external services
- Circuit breaker protection
- External API errors

Category: NetworkErrors - network communication and external service errors
(connection issues, timeouts, rate limit exceedances, circuit breaker opening,
and retry exhaustion).

All exceptions in this module inherit from RecoverableError, indicating that
retry with exponential backoff is appropriate (per RULES.md §3.1.3).

Sub-modules:
    connection: NetworkError, RetryExhaustedError
    timeout: TimeoutError, CircuitBreakerOpenError
    service: ApiError, ExternalServiceError, ServiceUnavailableError,
             RateLimitError, RateLimitExceededError, ServiceAuthenticationError,
             DataValidationError
"""

from __future__ import annotations

from bioetl.domain.exceptions.network.connection import (
    NetworkError,
    RetryExhaustedError,
)
from bioetl.domain.exceptions.network.service import (
    ApiError,
    DataValidationError,
    ExternalServiceError,
    RateLimitError,
    RateLimitExceededError,
    ServiceAuthenticationError,
    ServiceUnavailableError,
)
from bioetl.domain.exceptions.network.timeout import (
    CircuitBreakerOpenError,
    TimeoutError,
)

__all__ = [
    "ApiError",
    "CircuitBreakerOpenError",
    "DataValidationError",
    "ExternalServiceError",
    "NetworkError",
    "RateLimitError",
    "RateLimitExceededError",
    "RetryExhaustedError",
    "ServiceAuthenticationError",
    "ServiceUnavailableError",
    "TimeoutError",
]
