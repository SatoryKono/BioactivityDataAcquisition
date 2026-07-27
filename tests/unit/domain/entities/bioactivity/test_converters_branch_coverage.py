"""Branch coverage for bioactivity primitive converters (TD-R-02 / #6678)."""

from __future__ import annotations

import json

import pytest

from bioetl.domain.entities.bioactivity import _converters as converters


def test_safe_int_covers_null_bool_valid_and_invalid() -> None:
    assert converters._safe_int(None) is None
    assert converters._safe_int(True) is None
    assert converters._safe_int(False) is None
    assert converters._safe_int(" 42 ") == 42
    assert converters._safe_int("not-int") is None
    assert converters._safe_int(object()) is None


def test_safe_float_covers_null_bool_valid_and_invalid() -> None:
    assert converters._safe_float(None) is None
    assert converters._safe_float(True) is None
    assert converters._safe_float(" 3.5 ") == 3.5
    assert converters._safe_float("bad") is None
    assert converters._safe_float(object()) is None


def test_safe_str_and_require_field() -> None:
    assert converters._safe_str(None) is None
    assert converters._safe_str(12) == "12"
    assert converters._require_field({"id": 1}, "id") == 1
    with pytest.raises(ValueError, match="raw_data must contain"):
        converters._require_field({}, "id")


def test_safe_json_covers_all_branches() -> None:
    assert converters._safe_json(None) is None
    assert converters._safe_json("") is None
    assert json.loads(converters._safe_json({"a": 1}) or "") == {"a": 1}
    assert json.loads(converters._safe_json([1, 2]) or "") == [1, 2]
    assert json.loads(converters._safe_json((1, 2)) or "") == [1, 2]
    assert json.loads(converters._safe_json("x") or "") == {"value": "x"}
