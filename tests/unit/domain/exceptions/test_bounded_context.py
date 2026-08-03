# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
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
