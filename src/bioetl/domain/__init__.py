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
    Watermark,
)

__all__ = [
    # Exceptions - Base
    "BioETLError",
    "CriticalError",
    "RecoverableError",
    "DataQualityError",
    # Exceptions - Critical
    "LockLostError",
    "LockAcquisitionError",
    "CheckpointConflictError",
    "MergeConflictError",
    # Exceptions - Recoverable
    "RateLimitError",
    "RetryExhaustedError",
    "CircuitBreakerOpenError",
    "ApiError",
    "ChemblApiError",
    "StorageError",
    "BucketNotFoundError",
    "UploadError",
    "TableNotFoundError",
    # Exceptions - Data Quality
    "SchemaViolationError",
    "MissingRequiredFieldError",
    "InvalidDataFormatError",
    # Types
    "BatchID",
    "CircuitBreakerState",
    "ContentHash",
    "DQStatus",
    "DataClassification",
    "DriftLevel",
    "EntityID",
    "ErrorType",
    "HealthStatus",
    "RunID",
    "RunType",
    "Watermark",
]
