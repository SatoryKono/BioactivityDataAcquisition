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
from __future__ import annotations

import pytest
from bioetl.domain.behavior.composite_metadata_helpers import (
    _parse_literal,
    parse_composite_list,
    parse_composite_status,
)


pytestmark = pytest.mark.unit


def test_parse_literal_valid_json():
    assert _parse_literal('["a", "b"]') == ["a", "b"]
    assert _parse_literal('{"a": 1}') == {"a": 1}
    assert _parse_literal('"string"') == "string"
    assert _parse_literal("123") == 123


def test_parse_literal_legacy_fallback():
    # Single quotes are not valid JSON but should be handled by ast.literal_eval fallback
    assert _parse_literal("['a', 'b']") == ["a", "b"]
    assert _parse_literal("{'a': 1}") == {"a": 1}


def test_parse_literal_invalid_data():
    # Completely invalid
    assert _parse_literal("not json") is None
    # None for non-string input
    assert _parse_literal(None) is None
    assert _parse_literal(123) is None


def test_parse_composite_list_string():
    # Works with JSON (double quotes)
    assert parse_composite_list('["a", "b"]') == ["a", "b"]
    # Works with legacy (single quotes)
    assert parse_composite_list("['a', 'b']") == ["a", "b"]


def test_parse_composite_status_string():
    # Works with JSON (double quotes)
    assert parse_composite_status('{"a": "success"}') == {"a": "success"}
    # Works with legacy (single quotes)
    assert parse_composite_status("{'a': 'success'}") == {"a": "success"}


def test_parse_composite_list_actual_list():
    assert parse_composite_list(["a", "b"]) == ["a", "b"]


def test_parse_composite_status_actual_dict():
    assert parse_composite_status({"a": "success"}) == {"a": "success"}


if __name__ == "__main__":
    pytest.main([__file__])
