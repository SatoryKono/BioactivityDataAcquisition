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
    from bioetl.domain.exceptions._redaction import redact_string
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
    from bioetl.domain.exceptions.storage import (
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
    "redact_string",
]

_BASE_MODULE = "bioetl.domain.exceptions.base"
_BOUNDED_CONTEXT_MODULE = "bioetl.domain.exceptions.bounded_context"
_DATA_QUALITY_MODULE = "bioetl.domain.exceptions.data_quality"
_INFRASTRUCTURE_MODULE = "bioetl.domain.exceptions.storage"
_INTERNAL_MODULE = "bioetl.domain.exceptions.internal"
_NETWORK_MODULE = "bioetl.domain.exceptions.network"
_PIPELINE_SHUTDOWN_MODULE = "bioetl.domain.exceptions.pipeline_shutdown"
_VALIDATION_MODULE = "bioetl.domain.exceptions.validation"
_REDACTION_MODULE = "bioetl.domain.exceptions._redaction"

_EXPORT_MODULES = {
    "ApiError": _NETWORK_MODULE,
    "AuthFailureError": _INTERNAL_MODULE,
    "BioETLError": _BASE_MODULE,
    "BronzeValidationError": _INFRASTRUCTURE_MODULE,
    "BucketNotFoundError": _INFRASTRUCTURE_MODULE,
    "CachedBronzeEmptyError": _INFRASTRUCTURE_MODULE,
    "CheckpointConflictError": _INTERNAL_MODULE,
    "CircuitBreakerOpenError": _NETWORK_MODULE,
    "CriticalError": _BASE_MODULE,
    "DataQualityError": _BASE_MODULE,
    "DataQualityThresholdError": _DATA_QUALITY_MODULE,
    "DataValidationError": _NETWORK_MODULE,
    "DeltaOptimizeError": _INFRASTRUCTURE_MODULE,
    "DeltaSchemaValidationError": _INFRASTRUCTURE_MODULE,
    "DeltaTransactionError": _INFRASTRUCTURE_MODULE,
    "DeltaWriteConflictError": _INFRASTRUCTURE_MODULE,
    "DomainExceptionContext": _BOUNDED_CONTEXT_MODULE,
    "ExternalServiceError": _NETWORK_MODULE,
    "InfrastructureError": _INFRASTRUCTURE_MODULE,
    "InvalidStateError": _INTERNAL_MODULE,
    "LockAcquisitionError": _INTERNAL_MODULE,
    "LockLostError": _INTERNAL_MODULE,
    "MergeConflictError": _INTERNAL_MODULE,
    "MetricsServerError": _INTERNAL_MODULE,
    "NetworkError": _NETWORK_MODULE,
    "PipelineShutdownError": _PIPELINE_SHUTDOWN_MODULE,
    "PolicyViolationError": _INTERNAL_MODULE,
    "RateLimitError": _NETWORK_MODULE,
    "RateLimitExceededError": _NETWORK_MODULE,
    "redact_string": _REDACTION_MODULE,
    "RecoverableError": _BASE_MODULE,
    "RetryExhaustedError": _NETWORK_MODULE,
    "RunnerAlreadyExecutedError": _INTERNAL_MODULE,
    "SchemaEvolutionError": _INFRASTRUCTURE_MODULE,
    "SchemaViolationError": _VALIDATION_MODULE,
    "ServiceAuthenticationError": _NETWORK_MODULE,
    "ServiceUnavailableError": _NETWORK_MODULE,
    "ShutdownReason": _PIPELINE_SHUTDOWN_MODULE,
    "StorageError": _INFRASTRUCTURE_MODULE,
    "StorageQuotaExceededError": _INFRASTRUCTURE_MODULE,
    "TableNotFoundError": _INFRASTRUCTURE_MODULE,
    "TimeoutError": _NETWORK_MODULE,
    "UploadError": _INFRASTRUCTURE_MODULE,
    "ValidationError": _VALIDATION_MODULE,
    "get_domain_exception_context": _BOUNDED_CONTEXT_MODULE,
}


def __getattr__(name: str) -> object:  # pragma: no cover
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
