# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Golden tests for adapter error-category classification."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import (
    RateLimitExceededError,
    ServiceAuthenticationError,
    ServiceUnavailableError,
)
from bioetl.infrastructure.adapters.adapter_error_classifier import (
    AdapterErrorClassifier,
    ErrorCategory,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def classifier() -> AdapterErrorClassifier:
    logger = MagicMock()
    return AdapterErrorClassifier(classifier=ErrorClassifier(), logger=logger)


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, ErrorCategory.CRITICAL),
        (403, ErrorCategory.CRITICAL),
        (429, ErrorCategory.RECOVERABLE),
        (500, ErrorCategory.RECOVERABLE),
        (400, ErrorCategory.DATA_QUALITY),
        (404, ErrorCategory.DATA_QUALITY),
        (451, ErrorCategory.DATA_QUALITY),
        (599, ErrorCategory.RECOVERABLE),
    ],
)
def test_classify_http_status_golden(
    classifier: AdapterErrorClassifier,
    status_code: int,
    expected: ErrorCategory,
) -> None:
    assert classifier.classify_http_status(status_code) == expected


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            ServiceAuthenticationError("auth", service_name="chembl", status_code=401),
            ErrorCategory.CRITICAL,
        ),
        (
            RateLimitExceededError("limited", service_name="pubchem"),
            ErrorCategory.RECOVERABLE,
        ),
        (
            ServiceUnavailableError("timeout", service_name="uniprot"),
            ErrorCategory.RECOVERABLE,
        ),
        (
            ValueError("bad payload"),
            ErrorCategory.DATA_QUALITY,
        ),
    ],
)
def test_classify_exception_golden(
    classifier: AdapterErrorClassifier,
    error: Exception,
    expected: ErrorCategory,
) -> None:
    assert classifier.classify_exception(error) == expected


def test_classify_uses_status_precedence(
    classifier: AdapterErrorClassifier,
) -> None:
    error = ServiceAuthenticationError(
        "auth",
        service_name="crossref",
        status_code=401,
    )
    category = classifier.classify(error=error, status_code=500)
    assert category == ErrorCategory.RECOVERABLE
