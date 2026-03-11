"""Domain layer exceptions.

Implements centralized exception hierarchy for all BioETL errors.
All exceptions should inherit from BioETLError to enable consistent error handling.

Each exception class defines an explicit `error_type` attribute for deterministic
error classification (see ErrorClassifier).

Exception Categories (§7 RULES.md):
    - ValidationErrors: Schema and data format validation errors
    - DataQualityErrors: Batch-level data quality issues
    - NetworkErrors: Network connectivity and external service errors
    - InfrastructureErrors: Storage, filesystem, and environment errors
    - InternalErrors: Critical application errors requiring immediate attention

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

Provider-Specific Exceptions:
    Provider-specific API errors (CrossRefApiError, etc.) are
    defined in infrastructure.adapters.{provider}.exceptions. Application layer
    should catch ExternalServiceError instead.
"""

# =============================================================================
# Base Classes
# =============================================================================
from bioetl.domain.exceptions.base import (
    BioETLError,
    CriticalError,
    DataQualityError,
    RecoverableError,
)
from bioetl.domain.exceptions.bounded_context import (
    DomainExceptionContext,
    get_domain_exception_context,
)

# =============================================================================
# DataQualityErrors - Batch-level data quality issues
# =============================================================================
from bioetl.domain.exceptions.data_quality import (
    DataQualityThresholdError,
)

# =============================================================================
# InfrastructureErrors - Storage, filesystem, and environment errors
# =============================================================================
from bioetl.domain.exceptions.infrastructure import (
    BronzeValidationError,
    BucketNotFoundError,
    CachedBronzeEmptyError,
    DeltaOptimizeError,
    DeltaSchemaValidationError,
    DeltaTransactionError,
    DeltaWriteConflictError,
    InfrastructureError,
    SchemaEvolutionError,
    StorageError,
    StorageQuotaExceededError,
    TableNotFoundError,
    UploadError,
)

# =============================================================================
# InternalErrors - Critical application errors
# =============================================================================
from bioetl.domain.exceptions.internal import (
    AuthFailureError,
    CheckpointConflictError,
    InvalidStateError,
    LockAcquisitionError,
    LockLostError,
    MergeConflictError,
    MetricsServerError,
    PolicyViolationError,
    RunnerAlreadyExecutedError,
)

# =============================================================================
# NetworkErrors - Network connectivity and external service errors
# =============================================================================
from bioetl.domain.exceptions.network import (
    ApiError,
    CircuitBreakerOpenError,
    DataValidationError,
    ExternalServiceError,
    NetworkError,
    RateLimitError,
    RateLimitExceededError,
    RetryExhaustedError,
    ServiceAuthenticationError,
    ServiceUnavailableError,
    TimeoutError,
)

# =============================================================================
# PipelineShutdown - Graceful shutdown signal exception and reason enum
# =============================================================================
from bioetl.domain.exceptions.pipeline_shutdown import (
    PipelineShutdownError,
    ShutdownReason,
)

# =============================================================================
# ValidationErrors - Schema and data format validation
# =============================================================================
from bioetl.domain.exceptions.validation import (
    InvalidDataFormatError,
    MissingRequiredFieldError,
    SchemaViolationError,
    ValidationError,
)

__all__ = [
    "ApiError",
    "AuthFailureError",
    "BioETLError",
    "BronzeValidationError",
    "BucketNotFoundError",
    "CachedBronzeEmptyError",
    "CheckpointConflictError",
    "CircuitBreakerOpenError",
    "CriticalError",
    "DataQualityError",
    "DataQualityThresholdError",
    "DataValidationError",
    "DeltaOptimizeError",
    "DeltaSchemaValidationError",
    "DeltaTransactionError",
    "DeltaWriteConflictError",
    "DomainExceptionContext",
    "ExternalServiceError",
    "InfrastructureError",
    "InvalidDataFormatError",
    "InvalidStateError",
    "LockAcquisitionError",
    "LockLostError",
    "MergeConflictError",
    "MetricsServerError",
    "MissingRequiredFieldError",
    "NetworkError",
    "PipelineShutdownError",
    "PolicyViolationError",
    "RateLimitError",
    "RateLimitExceededError",
    "RecoverableError",
    "RetryExhaustedError",
    "RunnerAlreadyExecutedError",
    "SchemaEvolutionError",
    "SchemaViolationError",
    "ServiceAuthenticationError",
    "ServiceUnavailableError",
    "ShutdownReason",
    "StorageError",
    "StorageQuotaExceededError",
    "TableNotFoundError",
    "TimeoutError",
    "UploadError",
    "ValidationError",
    "get_domain_exception_context",
]
