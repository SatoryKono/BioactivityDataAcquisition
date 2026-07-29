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
"""Unit tests for shared adapter fetch/retry policy helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.exceptions import RetryExhaustedError
from bioetl.infrastructure.adapters.common.fetch_retry_policy import (
    TITLE_ONLY_MARKER_PREFIX,
    is_retry_exhausted_error,
    split_filter_ids_for_fallback,
)

pytestmark = pytest.mark.unit


class TestSplitFilterIdsForFallback:
    def test_splits_primary_and_title_only_markers(self) -> None:
        ids = ["CHEMBL1", f"{TITLE_ONLY_MARKER_PREFIX}foo", "  ", "CHEMBL2"]
        primary, title_only = split_filter_ids_for_fallback(ids)
        assert primary == ["CHEMBL1", "CHEMBL2"]
        assert title_only == [f"{TITLE_ONLY_MARKER_PREFIX}foo", "  "]


class TestIsRetryExhaustedError:
    def test_detects_direct_retry_exhausted(self) -> None:
        error = RetryExhaustedError("https://example.test", attempts=3)
        assert is_retry_exhausted_error(error) is True

    def test_detects_wrapped_retry_exhausted(self) -> None:
        try:
            raise RetryExhaustedError(
                "https://example.test", attempts=2
            ) from ValueError("outer")
        except RetryExhaustedError as exc:
            wrapped = RuntimeError("wrapper")
            wrapped.__cause__ = exc
            assert is_retry_exhausted_error(wrapped) is True

    def test_returns_false_for_unrelated_errors(self) -> None:
        assert is_retry_exhausted_error(ValueError("nope")) is False
