"""Domain-layer exception facade with lazy re-exports.

This module preserves historical `from bioetl.domain.exceptions import X` imports
without eagerly importing every exception module at package import time. Eager
re-export caused expensive import graphs and collection hangs in test/runtime
contexts that only needed one submodule.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
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
    from bioetl.domain.exceptions.pipeline_shutdown import (
        PipelineShutdownError,
        ShutdownReason,
    )
    from bioetl.domain.exceptions.validation import (
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
    "InvalidStateError",
    "LockAcquisitionError",
    "LockLostError",
    "MergeConflictError",
    "MetricsServerError",
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

_EXPORT_MODULES = {
    "ApiError": "bioetl.domain.exceptions.network",
    "AuthFailureError": "bioetl.domain.exceptions.internal",
    "BioETLError": "bioetl.domain.exceptions.base",
    "BronzeValidationError": "bioetl.domain.exceptions.infrastructure",
    "BucketNotFoundError": "bioetl.domain.exceptions.infrastructure",
    "CachedBronzeEmptyError": "bioetl.domain.exceptions.infrastructure",
    "CheckpointConflictError": "bioetl.domain.exceptions.internal",
    "CircuitBreakerOpenError": "bioetl.domain.exceptions.network",
    "CriticalError": "bioetl.domain.exceptions.base",
    "DataQualityError": "bioetl.domain.exceptions.base",
    "DataQualityThresholdError": "bioetl.domain.exceptions.data_quality",
    "DataValidationError": "bioetl.domain.exceptions.network",
    "DeltaOptimizeError": "bioetl.domain.exceptions.infrastructure",
    "DeltaSchemaValidationError": "bioetl.domain.exceptions.infrastructure",
    "DeltaTransactionError": "bioetl.domain.exceptions.infrastructure",
    "DeltaWriteConflictError": "bioetl.domain.exceptions.infrastructure",
    "DomainExceptionContext": "bioetl.domain.exceptions.bounded_context",
    "ExternalServiceError": "bioetl.domain.exceptions.network",
    "InfrastructureError": "bioetl.domain.exceptions.infrastructure",
    "InvalidStateError": "bioetl.domain.exceptions.internal",
    "LockAcquisitionError": "bioetl.domain.exceptions.internal",
    "LockLostError": "bioetl.domain.exceptions.internal",
    "MergeConflictError": "bioetl.domain.exceptions.internal",
    "MetricsServerError": "bioetl.domain.exceptions.internal",
    "NetworkError": "bioetl.domain.exceptions.network",
    "PipelineShutdownError": "bioetl.domain.exceptions.pipeline_shutdown",
    "PolicyViolationError": "bioetl.domain.exceptions.internal",
    "RateLimitError": "bioetl.domain.exceptions.network",
    "RateLimitExceededError": "bioetl.domain.exceptions.network",
    "RecoverableError": "bioetl.domain.exceptions.base",
    "RetryExhaustedError": "bioetl.domain.exceptions.network",
    "RunnerAlreadyExecutedError": "bioetl.domain.exceptions.internal",
    "SchemaEvolutionError": "bioetl.domain.exceptions.infrastructure",
    "SchemaViolationError": "bioetl.domain.exceptions.validation",
    "ServiceAuthenticationError": "bioetl.domain.exceptions.network",
    "ServiceUnavailableError": "bioetl.domain.exceptions.network",
    "ShutdownReason": "bioetl.domain.exceptions.pipeline_shutdown",
    "StorageError": "bioetl.domain.exceptions.infrastructure",
    "StorageQuotaExceededError": "bioetl.domain.exceptions.infrastructure",
    "TableNotFoundError": "bioetl.domain.exceptions.infrastructure",
    "TimeoutError": "bioetl.domain.exceptions.network",
    "UploadError": "bioetl.domain.exceptions.infrastructure",
    "ValidationError": "bioetl.domain.exceptions.validation",
    "get_domain_exception_context": "bioetl.domain.exceptions.bounded_context",
}


def __getattr__(name: str) -> object:  # pragma: no cover
    if TYPE_CHECKING:
        raise AttributeError
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
