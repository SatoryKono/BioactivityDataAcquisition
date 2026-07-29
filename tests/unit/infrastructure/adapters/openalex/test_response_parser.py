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
"""Unit tests for OpenAlex response parser helpers."""

from __future__ import annotations


import pytest

from bioetl.infrastructure.adapters.openalex.response_parser import (
    parse_openalex_next_cursor,
    parse_openalex_results,
)


pytestmark = pytest.mark.unit


class TestParseOpenAlexResults:
    """Tests for parse_openalex_results."""

    def test_returns_results_list(self) -> None:
        """Should return results list from payload."""
        payload = {"results": [{"id": "W1"}, {"id": "W2"}]}
        result = parse_openalex_results(payload)
        assert result == [{"id": "W1"}, {"id": "W2"}]

    def test_empty_results_list(self) -> None:
        """Should return empty list when results is empty."""
        payload = {"results": []}
        assert parse_openalex_results(payload) == []

    def test_missing_results_key(self) -> None:
        """Should return empty list when results key is absent."""
        payload = {"meta": {"count": 0}}
        assert parse_openalex_results(payload) == []

    def test_results_not_a_list(self) -> None:
        """Should return empty list when results is not a list."""
        payload = {"results": "not_a_list"}
        assert parse_openalex_results(payload) == []

    def test_results_is_none(self) -> None:
        """Should return empty list when results is None."""
        payload = {"results": None}
        assert parse_openalex_results(payload) == []

    def test_empty_payload(self) -> None:
        """Should return empty list for empty payload."""
        assert parse_openalex_results({}) == []


class TestParseOpenAlexNextCursor:
    """Tests for parse_openalex_next_cursor."""

    def test_returns_cursor_string(self) -> None:
        """Should return next_cursor from meta."""
        payload = {"meta": {"next_cursor": "abc123"}}
        assert parse_openalex_next_cursor(payload) == "abc123"

    def test_no_meta_key(self) -> None:
        """Should return None when meta is absent."""
        payload = {"results": []}
        assert parse_openalex_next_cursor(payload) is None

    def test_meta_not_dict(self) -> None:
        """Should return None when meta is not a dict."""
        payload = {"meta": "invalid"}
        assert parse_openalex_next_cursor(payload) is None

    def test_meta_is_none(self) -> None:
        """Should return None when meta is None."""
        payload = {"meta": None}
        assert parse_openalex_next_cursor(payload) is None

    def test_no_next_cursor_in_meta(self) -> None:
        """Should return None when next_cursor is absent from meta."""
        payload = {"meta": {"count": 100}}
        assert parse_openalex_next_cursor(payload) is None

    def test_next_cursor_not_string(self) -> None:
        """Should return None when next_cursor is not a string."""
        payload = {"meta": {"next_cursor": 12345}}
        assert parse_openalex_next_cursor(payload) is None

    def test_next_cursor_is_none(self) -> None:
        """Should return None when next_cursor is None (last page)."""
        payload = {"meta": {"next_cursor": None}}
        assert parse_openalex_next_cursor(payload) is None

    def test_empty_cursor_string(self) -> None:
        """Should return empty string cursor when present."""
        payload = {"meta": {"next_cursor": ""}}
        assert parse_openalex_next_cursor(payload) == ""
