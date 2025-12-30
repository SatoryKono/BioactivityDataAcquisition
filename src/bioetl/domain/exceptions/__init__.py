"""Domain layer exceptions.

Implements centralized exception hierarchy for all BioETL errors.
All exceptions should inherit from BioETLError to enable consistent error handling.

Each exception class defines an explicit `error_type` attribute for deterministic
error classification (see ErrorClassifier).

This module re-exports all exceptions for backward compatibility with:
    from bioetl.domain.exceptions import SomeError

External Service Exceptions (RULES.md §7.2):
    Domain layer provides abstract exceptions for external service errors.
    Application layer should catch these abstract exceptions, not provider-specific ones.

    - ExternalServiceError: Base for all external service errors
    - ServiceUnavailableError: Service is down (5xx, timeout)
    - RateLimitExceededError: Rate limit exceeded (429)
    - ServiceAuthenticationError: Auth failed (401/403)
    - DataValidationError: Invalid data from external source

Deprecated Exceptions:
    ChemblApiError and CrossRefApiError are deprecated in domain layer.
    Use infrastructure.adapters.{provider}.exceptions instead, and catch
    ExternalServiceError in application layer.
"""

from bioetl.domain.exceptions.base import (
    BioETLError,
    CriticalError,
    DataQualityError,
    RecoverableError,
)
from bioetl.domain.exceptions.critical import (
    AuthFailureError,
    CheckpointConflictError,
    InfrastructureError,
    InvalidStateError,
    LockAcquisitionError,
    LockLostError,
    MergeConflictError,
    PolicyViolationError,
)
from bioetl.domain.exceptions.data_quality import (
    DataQualityThresholdError,
    InvalidDataFormatError,
    MissingRequiredFieldError,
    SchemaViolationError,
)
from bioetl.domain.exceptions.external_service import (
    DataValidationError,
    ExternalServiceError,
    RateLimitExceededError,
    ServiceAuthenticationError,
    ServiceUnavailableError,
)
from bioetl.domain.exceptions.recoverable import (
    ApiError,
    ChemblApiError,
    CircuitBreakerOpenError,
    CrossRefApiError,
    NetworkError,
    RateLimitError,
    RetryExhaustedError,
    TimeoutError,
)
from bioetl.domain.exceptions.storage import (
    BronzeValidationError,
    BucketNotFoundError,
    SchemaEvolutionError,
    StorageError,
    TableNotFoundError,
    UploadError,
)

__all__ = [
    "ApiError",
    "AuthFailureError",
    "BioETLError",
    "BronzeValidationError",
    "BucketNotFoundError",
    "CheckpointConflictError",
    "ChemblApiError",
    "CircuitBreakerOpenError",
    "CriticalError",
    "CrossRefApiError",
    "DataQualityError",
    "DataQualityThresholdError",
    "DataValidationError",
    "ExternalServiceError",
    "InfrastructureError",
    "InvalidDataFormatError",
    "InvalidStateError",
    "LockAcquisitionError",
    "LockLostError",
    "MergeConflictError",
    "MissingRequiredFieldError",
    "NetworkError",
    "PolicyViolationError",
    "RateLimitError",
    "RateLimitExceededError",
    "RecoverableError",
    "RetryExhaustedError",
    "SchemaEvolutionError",
    "SchemaViolationError",
    "ServiceAuthenticationError",
    "ServiceUnavailableError",
    "StorageError",
    "TableNotFoundError",
    "TimeoutError",
    "UploadError",
]
