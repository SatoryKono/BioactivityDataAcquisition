"""Bounded-context taxonomy for domain exceptions."""

from __future__ import annotations

from enum import StrEnum

from bioetl.domain.exceptions.base import (
    BioETLError,
    DataQualityError,
    RecoverableError,
)
from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.exceptions.infrastructure import InfrastructureError, StorageError
from bioetl.domain.exceptions.internal import (
    CheckpointConflictError,
    InvalidStateError,
    MergeConflictError,
    PolicyViolationError,
    RunnerAlreadyExecutedError,
)
from bioetl.domain.exceptions.network import ExternalServiceError, NetworkError
from bioetl.domain.exceptions.validation import ValidationError

__all__ = ["DomainExceptionContext", "get_domain_exception_context"]


class DomainExceptionContext(StrEnum):
    """Bounded contexts used for exception taxonomy and governance."""

    DATA_QUALITY = "data_quality"
    EXTERNAL_INTEGRATION = "external_integration"
    ORCHESTRATION = "orchestration"
    PLATFORM = "platform"
    STORAGE = "storage"
    VALIDATION = "validation"


_CONTEXT_CLASS_MAP: dict[DomainExceptionContext, tuple[type[BioETLError], ...]] = {
    DomainExceptionContext.EXTERNAL_INTEGRATION: (ExternalServiceError, NetworkError),
    DomainExceptionContext.STORAGE: (StorageError, InfrastructureError),
    DomainExceptionContext.ORCHESTRATION: (
        CheckpointConflictError,
        InvalidStateError,
        MergeConflictError,
        PolicyViolationError,
        RunnerAlreadyExecutedError,
    ),
    DomainExceptionContext.VALIDATION: (ValidationError,),
    DomainExceptionContext.DATA_QUALITY: (DataQualityThresholdError, DataQualityError),
}


def get_domain_exception_context(
    error_or_type: BioETLError | type[BioETLError],
) -> DomainExceptionContext:
    """Resolve domain exception into a bounded context.

    Args:
        error_or_type: A BioETLError instance or its class to classify.

    Returns:
        DomainExceptionContext enum value identifying the bounded context of the error.
    """
    error_type = (
        error_or_type if isinstance(error_or_type, type) else type(error_or_type)
    )

    for context, class_family in _CONTEXT_CLASS_MAP.items():
        if issubclass(error_type, class_family):
            return context

    if issubclass(error_type, RecoverableError):
        return DomainExceptionContext.EXTERNAL_INTEGRATION
    return DomainExceptionContext.PLATFORM
