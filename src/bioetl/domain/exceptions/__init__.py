"""bioetl.domain.exceptions - centralized exception package.

This package re-exports exception classes from submodules for backward compatibility.
"""

# Re-export exceptions from submodules for compatibility
from bioetl.domain.exceptions.base import (
    BioETLError,
    CriticalError,
    RecoverableError,
)
from bioetl.domain.exceptions.data_quality import (
    DataQualityError,
    DataQualityThresholdError,
)
from bioetl.domain.exceptions.infrastructure import (
    BronzeValidationError,
    BucketNotFoundError,
    CheckpointConflictError,
    DeltaOptimizeError,
    DeltaSchemaValidationError,
    DeltaTransactionError,
    DeltaWriteConflictError,
    InfrastructureError,
    LockAcquisitionError,
    LockLostError,
    MergeConflictError,
    SchemaEvolutionError,
    StorageError,
    StorageQuotaExceededError,
    TableNotFoundError,
    UploadError,
)
from bioetl.domain.exceptions.internal import (
    AuthFailureError,
    InternalError,
    InvalidStateError,
    PolicyViolationError,
)
from bioetl.domain.exceptions.network import (
    ApiError,
    CircuitBreakerOpenError,
    ConnectionError,
    ExternalServiceError,
    NetworkError,
    RateLimitError,
    RateLimitExceededError,
    RetryExhaustedError,
    ServiceAuthenticationError,
    ServiceUnavailableError,
    TimeoutError,
)
from bioetl.domain.exceptions.validation import (
    ExternalDataValidationError,
    InvalidDataFormatError,
    MissingRequiredFieldError,
    SchemaValidationError,
    ValidationError,
)

# Aliases for backward compatibility
DataValidationError = ExternalDataValidationError
SchemaViolationError = SchemaValidationError

__all__ = [  # noqa: RUF022
    # Base
    "BioETLError",
    "CriticalError",
    "RecoverableError",
    # Validation
    "ValidationError",
    "SchemaValidationError",
    "MissingRequiredFieldError",
    "InvalidDataFormatError",
    "ExternalDataValidationError",
    "DataValidationError",  # Alias
    # Data Quality
    "DataQualityError",
    "DataQualityThresholdError",
    "SchemaViolationError",  # Alias
    # Network
    "NetworkError",
    "TimeoutError",
    "ConnectionError",
    "RateLimitError",
    "RetryExhaustedError",
    "CircuitBreakerOpenError",
    "ExternalServiceError",
    "ServiceUnavailableError",
    "RateLimitExceededError",
    "ServiceAuthenticationError",
    "ApiError",
    # Infrastructure
    "InfrastructureError",
    "StorageError",
    "BucketNotFoundError",
    "TableNotFoundError",
    "UploadError",
    "SchemaEvolutionError",
    "DeltaOptimizeError",
    "LockAcquisitionError",
    "LockLostError",
    "CheckpointConflictError",
    "MergeConflictError",
    "DeltaTransactionError",
    "StorageQuotaExceededError",
    "DeltaWriteConflictError",
    "BronzeValidationError",
    "DeltaSchemaValidationError",
    # Internal
    "InternalError",
    "PolicyViolationError",
    "InvalidStateError",
    "AuthFailureError",
]
