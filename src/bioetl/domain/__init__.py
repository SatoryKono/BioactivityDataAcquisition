"""Domain layer: entities, value objects, and ports."""

# Exceptions
from bioetl.domain.exceptions import (
    ApiError,
    BioETLError,
    BucketNotFoundError,
    CheckpointConflictError,
    ChemblApiError,
    CircuitBreakerOpenError,
    CriticalError,
    DataQualityError,
    InvalidDataFormatError,
    LockAcquisitionError,
    LockLostError,
    MergeConflictError,
    MissingRequiredFieldError,
    RateLimitError,
    RecoverableError,
    RetryExhaustedError,
    SchemaViolationError,
    StorageError,
    TableNotFoundError,
    UploadError,
)

# Types
from bioetl.domain.types import (
    BatchID,
    CircuitBreakerState,
    ContentHash,
    DataClassification,
    DQStatus,
    DriftLevel,
    EntityID,
    ErrorType,
    HealthStatus,
    RunID,
    RunType,
)

__all__ = [
    "ApiError",
    # Types
    "BatchID",
    # Exceptions - Base
    "BioETLError",
    "BucketNotFoundError",
    "CheckpointConflictError",
    "ChemblApiError",
    "CircuitBreakerOpenError",
    "CircuitBreakerState",
    "ContentHash",
    "CriticalError",
    "DQStatus",
    "DataClassification",
    "DataQualityError",
    "DriftLevel",
    "EntityID",
    "ErrorType",
    "HealthStatus",
    "InvalidDataFormatError",
    "LockAcquisitionError",
    # Exceptions - Critical
    "LockLostError",
    "MergeConflictError",
    "MissingRequiredFieldError",
    # Exceptions - Recoverable
    "RateLimitError",
    "RecoverableError",
    "RetryExhaustedError",
    "RunID",
    "RunType",
    # Exceptions - Data Quality
    "SchemaViolationError",
    "StorageError",
    "TableNotFoundError",
    "UploadError",
]
