"""Domain layer exceptions.

Implements centralized exception hierarchy for all BioETL errors.
All exceptions should inherit from BioETLError to enable consistent error handling.

Each exception class defines an explicit `error_type` attribute for deterministic
error classification (see ErrorClassifier).

This module re-exports all exceptions for backward compatibility with:
    from bioetl.domain.exceptions import SomeError
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
    "RecoverableError",
    "RetryExhaustedError",
    "SchemaEvolutionError",
    "SchemaViolationError",
    "StorageError",
    "TableNotFoundError",
    "TimeoutError",
    "UploadError",
]
