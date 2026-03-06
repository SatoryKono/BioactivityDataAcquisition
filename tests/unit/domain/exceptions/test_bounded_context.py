"""Contract tests for bounded-context exception taxonomy."""

from __future__ import annotations

import pytest

from bioetl.domain.exceptions import (
    DataQualityThresholdError,
    DomainExceptionContext,
    ExternalServiceError,
    PolicyViolationError,
    SchemaViolationError,
    StorageError,
    get_domain_exception_context,
)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            ExternalServiceError("network", service_name="chembl"),
            DomainExceptionContext.EXTERNAL_INTEGRATION,
        ),
        (StorageError("storage unavailable"), DomainExceptionContext.STORAGE),
        (
            PolicyViolationError("invalid write mode"),
            DomainExceptionContext.ORCHESTRATION,
        ),
        (
            SchemaViolationError("chembl_activity", ["missing id"]),
            DomainExceptionContext.VALIDATION,
        ),
        (
            DataQualityThresholdError(error_rate=0.30, threshold=0.20),
            DomainExceptionContext.DATA_QUALITY,
        ),
    ],
)
def test_get_domain_exception_context_from_instance(
    error: Exception,
    expected: DomainExceptionContext,
) -> None:
    assert get_domain_exception_context(error) == expected


@pytest.mark.parametrize(
    ("error_type", "expected"),
    [
        (ExternalServiceError, DomainExceptionContext.EXTERNAL_INTEGRATION),
        (StorageError, DomainExceptionContext.STORAGE),
        (PolicyViolationError, DomainExceptionContext.ORCHESTRATION),
        (SchemaViolationError, DomainExceptionContext.VALIDATION),
    ],
)
def test_get_domain_exception_context_from_type(
    error_type: type[Exception],
    expected: DomainExceptionContext,
) -> None:
    assert get_domain_exception_context(error_type) == expected
