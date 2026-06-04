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
