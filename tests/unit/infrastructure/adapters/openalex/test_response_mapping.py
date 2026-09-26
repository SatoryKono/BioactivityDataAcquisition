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
"""Tests for OpenAlex response mapping helpers."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.openalex.response_mapping import (
    OpenAlexResponseMapper,
)

pytestmark = pytest.mark.unit


def test_extract_results_filters_non_mapping_items() -> None:
    mapper = OpenAlexResponseMapper()

    result = mapper.extract_results(
        {"results": [{"id": "W1"}, "bad-record", None, {"id": "W2"}]}
    )

    assert result == [{"id": "W1"}, {"id": "W2"}]


def test_extract_next_cursor_returns_none_without_meta_mapping() -> None:
    mapper = OpenAlexResponseMapper()

    assert mapper.extract_next_cursor({"meta": "invalid"}) is None


def test_extract_next_cursor_returns_text_cursor_from_meta() -> None:
    mapper = OpenAlexResponseMapper()

    assert mapper.extract_next_cursor({"meta": {"next_cursor": "cursor-2"}}) == (
        "cursor-2"
    )


def test_mark_lookup_sets_lookup_metadata_fields() -> None:
    mapper = OpenAlexResponseMapper()

    mapped = mapper.mark_lookup(
        {"id": "W1"},
        lookup_method="title",
        original_id="OA:W1",
        search_title="Example title",
    )

    assert mapped == {
        "id": "W1",
        "_lookup_method": "title",
        "_original_id": "OA:W1",
        "_search_title": "Example title",
    }


def test_mark_lookup_omits_optional_fields_when_absent() -> None:
    mapper = OpenAlexResponseMapper()

    mapped = mapper.mark_lookup({"id": "W2"}, lookup_method="doi")

    assert mapped == {
        "id": "W2",
        "_lookup_method": "doi",
    }
