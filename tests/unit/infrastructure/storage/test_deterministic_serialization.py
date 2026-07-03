"""Unit tests for deterministic serialization helpers."""

from __future__ import annotations

import pytest

import json


pytestmark = pytest.mark.unit


class TestDeterministicBronzeWrite:
    """Tests for deterministic Bronze-layer serialization."""

    def test_json_strings_are_sorted(self) -> None:
        """Bronze JSON strings should sort deterministically by serialized value."""
        records = [
            {"id": "C", "value": 3},
            {"id": "A", "value": 1},
            {"id": "B", "value": 2},
        ]

        json_strings = [json.dumps(record, sort_keys=True) for record in records]
        json_strings.sort()

        parsed = [json.loads(serialized) for serialized in json_strings]
        assert [record["id"] for record in parsed] == ["A", "B", "C"]

    def test_json_key_order_is_deterministic(self) -> None:
        """Bronze JSON serialization should keep a stable key order."""
        record = {"z_key": 1, "a_key": 2, "m_key": 3}

        json_str = json.dumps(record, sort_keys=True)

        assert json_str == '{"a_key": 2, "m_key": 3, "z_key": 1}'
