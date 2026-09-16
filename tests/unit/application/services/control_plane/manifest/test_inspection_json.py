"""Tests for lossless JSON normalization used by manifest inspection."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.manifest._inspection_json import (
    normalize_jsonable,
    normalize_typed_jsonable,
)

pytestmark = pytest.mark.unit


def test_normalize_typed_jsonable_preserves_scalar_type_identity() -> None:
    aware = datetime(2026, 1, 2, 3, 4, tzinfo=UTC)
    naive = datetime(2026, 1, 2, 3, 4)
    assert normalize_typed_jsonable(aware) == {
        "__type__": "datetime",
        "isoformat": aware.isoformat(),
        "aware": True,
        "tz": "UTC",
    }
    assert cast(dict[str, Any], normalize_typed_jsonable(naive))["aware"] is False
    assert cast(dict[str, Any], normalize_typed_jsonable(date(2026, 1, 2)))[
        "__type__"
    ] == "date"
    assert cast(dict[str, Any], normalize_typed_jsonable(UUID(int=1)))[
        "__type__"
    ] == "uuid"
    assert normalize_typed_jsonable(b"\x00\xff") == {
        "__type__": "bytes",
        "hex": "00ff",
    }
    assert normalize_typed_jsonable(object()) is None


def test_normalize_jsonable_recurses_and_sorts_unordered_values() -> None:
    value = {
        1: (UUID(int=2), b"a"),
        "set": frozenset({"b", "a"}),
        "plain": [None, True, 2, 3.5, "x"],
    }
    normalized = cast(dict[str, Any], normalize_jsonable(value))
    assert normalized["1"][0]["__type__"] == "uuid"
    assert normalized["1"][1] == {"__type__": "bytes", "hex": "61"}
    assert normalized["set"] == ["a", "b"]
    assert normalized["plain"] == [None, True, 2, 3.5, "x"]


def test_normalize_jsonable_marks_unsupported_value() -> None:
    class StableUnsupported:
        def __repr__(self) -> str:
            return "stable-value"

    assert normalize_jsonable(StableUnsupported()) == {
        "__type__": "unsupported",
        "qualname": "test_normalize_jsonable_marks_unsupported_value.<locals>.StableUnsupported",
        "repr": "stable-value",
    }
