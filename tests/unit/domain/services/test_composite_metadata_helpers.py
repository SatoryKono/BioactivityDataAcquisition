from __future__ import annotations

import pytest
from bioetl.domain.services.composite_metadata_helpers import (
    _parse_literal,
    parse_composite_list,
    parse_composite_status,
)


def test_parse_literal_valid_json():
    assert _parse_literal('["a", "b"]') == ["a", "b"]
    assert _parse_literal('{"a": 1}') == {"a": 1}
    assert _parse_literal('"string"') == "string"
    assert _parse_literal("123") == 123


def test_parse_literal_invalid_json():
    # Single quotes are not valid JSON
    assert _parse_literal("['a', 'b']") is None
    # Completely invalid
    assert _parse_literal("not json") is None
    # None for non-string input
    assert _parse_literal(None) is None
    assert _parse_literal(123) is None


def test_parse_composite_list_string():
    # Now requires JSON (double quotes)
    assert parse_composite_list('["a", "b"]') == ["a", "b"]
    # Single quotes fail
    assert parse_composite_list("['a', 'b']") == []


def test_parse_composite_status_string():
    # Now requires JSON (double quotes)
    assert parse_composite_status('{"a": "success"}') == {"a": "success"}
    # Single quotes fail
    assert parse_composite_status("{'a': 'success'}") == {}


def test_parse_composite_list_actual_list():
    assert parse_composite_list(["a", "b"]) == ["a", "b"]


def test_parse_composite_status_actual_dict():
    assert parse_composite_status({"a": "success"}) == {"a": "success"}


if __name__ == "__main__":
    pytest.main([__file__])
