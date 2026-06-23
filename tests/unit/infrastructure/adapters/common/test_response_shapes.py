"""Tests for shared adapter response-shaping helpers."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.common.response_shapes import (
    extract_response_items,
    extract_response_mapping,
    extract_response_text,
    normalize_response_items,
)


pytestmark = pytest.mark.unit


def test_normalize_response_items_supports_lists_and_tuples() -> None:
    assert normalize_response_items([1, 2]) == [1, 2]
    assert normalize_response_items((1, 2)) == [1, 2]


def test_normalize_response_items_rejects_non_sequence_payloads() -> None:
    assert normalize_response_items(None) == []
    assert normalize_response_items({"results": []}) == []
    assert normalize_response_items("not-a-sequence") == []


def test_extract_response_items_normalizes_missing_or_malformed_fields() -> None:
    assert extract_response_items({"results": [{"id": 1}]}, "results") == [{"id": 1}]
    assert extract_response_items({"results": (1, 2)}, "results") == [1, 2]
    assert extract_response_items({"results": "bad"}, "results") == []
    assert extract_response_items({}, "results") == []


def test_extract_response_mapping_returns_only_mapping_values() -> None:
    assert extract_response_mapping({"meta": {"next_cursor": "abc"}}, "meta") == {
        "next_cursor": "abc"
    }
    assert extract_response_mapping({"meta": []}, "meta") is None
    assert extract_response_mapping({}, "meta") is None


def test_extract_response_text_returns_only_string_values() -> None:
    assert extract_response_text({"nextCursor": "cursor-1"}, "nextCursor") == "cursor-1"
    assert extract_response_text({"nextCursor": 10}, "nextCursor") is None
    assert extract_response_text({}, "nextCursor") is None


def test_extract_response_text_handles_empty_strings() -> None:
    assert extract_response_text({"key": ""}, "key") == ""


def test_extract_response_text_rejects_booleans_and_none() -> None:
    assert extract_response_text({"key": True}, "key") is None
    assert extract_response_text({"key": False}, "key") is None
    assert extract_response_text({"key": None}, "key") is None
