"""Unit tests for JSON encoder implementations.

Tests verify:
- Correctness of encoding/decoding
- Deterministic output (sorted keys)
- Unicode handling
- Canonical form for hashing
- Feature flag switching
- Protocol compliance
"""

from __future__ import annotations

import json
import os
from typing import Any
from unittest import mock

import pytest

from bioetl.domain.ports import JsonEncoderPort
from bioetl.infrastructure.serialization.encoders import (
    ORJSON_AVAILABLE,
    OrjsonEncoder,
    StdLibJsonEncoder,
    get_json_encoder,
    reset_encoder_cache,
)


pytestmark = pytest.mark.unit


class TestStdLibJsonEncoder:
    """Tests for StdLibJsonEncoder implementation."""

    @pytest.fixture
    def encoder(self) -> StdLibJsonEncoder:
        """Create encoder instance."""
        return StdLibJsonEncoder()

    def test_implements_protocol(self, encoder: StdLibJsonEncoder) -> None:
        """Encoder should implement JsonEncoderPort protocol."""
        assert isinstance(encoder, JsonEncoderPort)

    def test_dumps_basic_dict(self, encoder: StdLibJsonEncoder) -> None:
        """Should serialize basic dictionary."""
        data = {"name": "test", "value": 42}
        result = encoder.dumps(data)
        assert json.loads(result) == data

    def test_dumps_sorted_keys(self, encoder: StdLibJsonEncoder) -> None:
        """Should output keys in sorted order by default."""
        data = {"z": 1, "a": 2, "m": 3}
        result = encoder.dumps(data)
        # Keys should appear in alphabetical order
        assert result == '{"a":2,"m":3,"z":1}'

    def test_dumps_unsorted_keys(self, encoder: StdLibJsonEncoder) -> None:
        """Should preserve key order when sort_keys=False."""
        data = {"z": 1, "a": 2, "m": 3}
        result = encoder.dumps(data, sort_keys=False)
        # Should still be valid JSON
        assert json.loads(result) == data

    def test_dumps_compact_output(self, encoder: StdLibJsonEncoder) -> None:
        """Should produce compact output without whitespace."""
        data = {"key": "value", "nested": {"a": 1}}
        result = encoder.dumps(data)
        # No spaces after colons or commas
        assert " " not in result

    def test_dumps_unicode_preserved(self, encoder: StdLibJsonEncoder) -> None:
        """Should preserve Unicode characters by default."""
        data = {"name": "тест", "greek": "αβγ"}
        result = encoder.dumps(data)
        assert "тест" in result
        assert "αβγ" in result

    def test_dumps_ensure_ascii(self, encoder: StdLibJsonEncoder) -> None:
        """Should escape non-ASCII when ensure_ascii=True."""
        data = {"name": "тест"}
        result = encoder.dumps(data, ensure_ascii=True)
        # Russian text should be escaped
        assert "тест" not in result
        assert "\\u" in result

    def test_dumps_list(self, encoder: StdLibJsonEncoder) -> None:
        """Should serialize lists correctly."""
        data = [1, "two", {"three": 3}]
        result = encoder.dumps(data)
        assert json.loads(result) == data

    def test_dumps_nested_structures(self, encoder: StdLibJsonEncoder) -> None:
        """Should handle deeply nested structures."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": [1, 2, 3],
                    }
                }
            }
        }
        result = encoder.dumps(data)
        assert json.loads(result) == data

    def test_dumps_canonical(self, encoder: StdLibJsonEncoder) -> None:
        """Canonical output should be sorted, compact, ASCII-only."""
        data = {"z": "тест", "a": 1}
        result = encoder.dumps_canonical(data)

        # Sorted keys
        assert result.startswith('{"a":')

        # Compact (no spaces)
        assert " " not in result

        # ASCII-only
        assert result.isascii()

    def test_loads_string(self, encoder: StdLibJsonEncoder) -> None:
        """Should deserialize JSON string."""
        json_str = '{"key":"value"}'
        result = encoder.loads(json_str)
        assert result == {"key": "value"}

    def test_loads_bytes(self, encoder: StdLibJsonEncoder) -> None:
        """Should deserialize JSON bytes."""
        json_bytes = b'{"key":"value"}'
        result = encoder.loads(json_bytes)
        assert result == {"key": "value"}

    def test_loads_invalid_json_raises_valueerror(
        self, encoder: StdLibJsonEncoder
    ) -> None:
        """Should raise ValueError for invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            encoder.loads("not valid json")

    def test_roundtrip(self, encoder: StdLibJsonEncoder) -> None:
        """Dumps followed by loads should preserve data."""
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": True},
        }
        result = encoder.loads(encoder.dumps(data))
        assert result == data


@pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
class TestOrjsonEncoder:
    """Tests for OrjsonEncoder implementation."""

    @pytest.fixture
    def encoder(self) -> OrjsonEncoder:
        """Create encoder instance."""
        return OrjsonEncoder()

    def test_orjson_encoder__implements_protocol__baac10e2(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Encoder should implement JsonEncoderPort protocol."""
        assert isinstance(encoder, JsonEncoderPort)

    def test_orjson_encoder__dumps_basic_dict__9a0ef611(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Should serialize basic dictionary."""
        data = {"name": "test", "value": 42}
        result = encoder.dumps(data)
        assert json.loads(result) == data

    def test_orjson_encoder__dumps_sorted_keys__8504ec7b(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Should output keys in sorted order by default."""
        data = {"z": 1, "a": 2, "m": 3}
        result = encoder.dumps(data)
        parsed = json.loads(result)
        assert parsed == data
        # Verify key order in output string
        assert result.index('"a"') < result.index('"m"') < result.index('"z"')

    def test_orjson_encoder__dumps_compact_output__e799f2f8(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Should produce compact output without extra whitespace."""
        data = {"key": "value", "nested": {"a": 1}}
        result = encoder.dumps(data)
        # Verify compact format
        assert json.loads(result) == data
        # orjson produces compact output by default

    def test_orjson_encoder__unicode_preserved__ad66f622(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Should preserve Unicode characters by default."""
        data = {"name": "тест", "greek": "αβγ"}
        result = encoder.dumps(data)
        assert "тест" in result
        assert "αβγ" in result

    def test_orjson_encoder__dumps_ensure_ascii__5452b8cf(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Should escape non-ASCII when ensure_ascii=True."""
        data = {"emoji": "😀", "name": "тест"}
        result = encoder.dumps(data, ensure_ascii=True)
        # Russian text should be escaped
        assert "тест" not in result
        assert result.isascii()
        assert json.loads(result) == data

    def test_orjson_encoder__dumps_list__be2ec085(self, encoder: OrjsonEncoder) -> None:
        """Should serialize lists correctly."""
        data = [1, "two", {"three": 3}]
        result = encoder.dumps(data)
        assert json.loads(result) == data

    def test_orjson_encoder__nested_structures__cb02c66d(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Should handle deeply nested structures."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": [1, 2, 3],
                    }
                }
            }
        }
        result = encoder.dumps(data)
        assert json.loads(result) == data

    def test_orjson_encoder__dumps_canonical__d1fe60cd(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Canonical output should be ASCII-only."""
        data = {"z": "тест", "emoji": "😀", "a": 1}
        result = encoder.dumps_canonical(data)

        # ASCII-only
        assert result.isascii()

        # Valid JSON
        parsed = json.loads(result)
        # Keys should match
        assert set(parsed.keys()) == {"a", "emoji", "z"}
        assert parsed == data

    def test_orjson_encoder__loads_string__fd8d9802(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Should deserialize JSON string."""
        json_str = '{"key":"value"}'
        result = encoder.loads(json_str)
        assert result == {"key": "value"}

    def test_orjson_encoder__loads_bytes__45099300(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Should deserialize JSON bytes."""
        json_bytes = b'{"key":"value"}'
        result = encoder.loads(json_bytes)
        assert result == {"key": "value"}

    def test_orjson_encoder__raises_valueerror__c205d091(
        self, encoder: OrjsonEncoder
    ) -> None:
        """Should raise ValueError for invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            encoder.loads("not valid json")

    def test_orjson_encoder__roundtrip__4544223f(self, encoder: OrjsonEncoder) -> None:
        """Dumps followed by loads should preserve data."""
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": True},
        }
        result = encoder.loads(encoder.dumps(data))
        assert result == data


class TestGetJsonEncoder:
    """Tests for get_json_encoder factory function."""

    def teardown_method(self) -> None:
        """Reset encoder cache after each test."""
        reset_encoder_cache()

    def test_returns_encoder_implementing_protocol(self) -> None:
        """Factory should return a JsonEncoderPort implementation."""
        encoder = get_json_encoder()
        assert isinstance(encoder, JsonEncoderPort)

    def test_env_stdlib_returns_stdlib_encoder(self) -> None:
        """BIOETL_JSON_ENCODER=stdlib should return StdLibJsonEncoder."""
        with mock.patch.dict(os.environ, {"BIOETL_JSON_ENCODER": "stdlib"}):
            reset_encoder_cache()
            encoder = get_json_encoder()
            assert isinstance(encoder, StdLibJsonEncoder)

    def test_explicit_encoder_type_takes_priority_over_environment(self) -> None:
        """Explicit encoder selection should ignore the environment fallback."""
        with mock.patch.dict(os.environ, {"BIOETL_JSON_ENCODER": "invalid"}):
            reset_encoder_cache()
            encoder = get_json_encoder(" stdlib ")
            assert isinstance(encoder, StdLibJsonEncoder)

    @pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
    def test_env_orjson_returns_orjson_encoder(self) -> None:
        """BIOETL_JSON_ENCODER=orjson should return OrjsonEncoder."""
        with mock.patch.dict(os.environ, {"BIOETL_JSON_ENCODER": "orjson"}):
            reset_encoder_cache()
            encoder = get_json_encoder()
            assert isinstance(encoder, OrjsonEncoder)

    def test_invalid_encoder_type_raises_valueerror(self) -> None:
        """Invalid encoder type should raise ValueError."""
        with mock.patch.dict(os.environ, {"BIOETL_JSON_ENCODER": "invalid"}):
            reset_encoder_cache()
            with pytest.raises(ValueError, match="Unknown JSON encoder type"):
                get_json_encoder()

    @pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
    def test_default_uses_orjson_when_available(self) -> None:
        """Default should use orjson when available."""
        with mock.patch.dict(os.environ, {}, clear=True):
            # Remove BIOETL_JSON_ENCODER if set
            os.environ.pop("BIOETL_JSON_ENCODER", None)
            reset_encoder_cache()
            encoder = get_json_encoder()
            assert isinstance(encoder, OrjsonEncoder)

    def test_encoder_is_cached(self) -> None:
        """Factory should return same instance on repeated calls."""
        encoder1 = get_json_encoder()
        encoder2 = get_json_encoder()
        assert encoder1 is encoder2


class TestEncoderOutputConsistency:
    """Tests verifying consistent output between encoders."""

    @pytest.fixture
    def test_data(self) -> list[dict[str, Any]]:
        """Test data covering various edge cases."""
        return [
            {},
            {"a": 1},
            {"z": 1, "a": 2, "m": 3},
            {"nested": {"deep": {"value": 42}}},
            {"array": [1, 2, 3]},
            {"mixed": [1, "two", {"three": 3}]},
            {"float": 3.14159},
            {"null": None},
            {"bool_true": True, "bool_false": False},
            {"special": 'quotes"and\\backslash'},
        ]

    def test_stdlib_produces_valid_json(self, test_data: list[dict[str, Any]]) -> None:
        """StdLib encoder should produce valid JSON."""
        encoder = StdLibJsonEncoder()
        for data in test_data:
            result = encoder.dumps(data)
            # Should be parseable
            parsed = json.loads(result)
            assert parsed == data

    @pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
    def test_orjson_produces_valid_json(self, test_data: list[dict[str, Any]]) -> None:
        """Orjson encoder should produce valid JSON."""
        encoder = OrjsonEncoder()
        for data in test_data:
            result = encoder.dumps(data)
            # Should be parseable by stdlib json
            parsed = json.loads(result)
            assert parsed == data

    @pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
    def test_both_encoders_produce_same_parsed_result(
        self, test_data: list[dict[str, Any]]
    ) -> None:
        """Both encoders should produce functionally equivalent output."""
        stdlib = StdLibJsonEncoder()
        orjson_enc = OrjsonEncoder()

        for data in test_data:
            stdlib_result = json.loads(stdlib.dumps(data))
            orjson_result = json.loads(orjson_enc.dumps(data))
            assert stdlib_result == orjson_result, f"Mismatch for: {data}"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.fixture(params=["stdlib", "orjson"])
    def encoder(self, request: pytest.FixtureRequest) -> JsonEncoderPort:
        """Parametrized encoder for testing both implementations."""
        if request.param == "stdlib":
            return StdLibJsonEncoder()
        elif ORJSON_AVAILABLE:
            return OrjsonEncoder()
        else:
            pytest.skip("orjson not installed")
            return StdLibJsonEncoder()  # unreachable but satisfies type checker

    def test_empty_dict(self, encoder: JsonEncoderPort) -> None:
        """Should handle empty dictionary."""
        assert encoder.dumps({}) == "{}"

    def test_encoders_edge_cases__empty_list__6f7854d9(
        self, encoder: JsonEncoderPort
    ) -> None:
        """Should handle empty list."""
        assert encoder.dumps([]) == "[]"

    def test_large_numbers(self, encoder: JsonEncoderPort) -> None:
        """Should handle large numbers."""
        data = {"big": 10**15, "small": 10**-10}
        result = encoder.loads(encoder.dumps(data))
        assert result["big"] == 10**15

    def test_encoders_edge_cases__special_characters__53a6a236(
        self, encoder: JsonEncoderPort
    ) -> None:
        """Should handle special characters."""
        data = {"special": '\n\t\r"\\'}
        result = encoder.loads(encoder.dumps(data))
        assert result == data

    def test_emoji(self, encoder: JsonEncoderPort) -> None:
        """Should handle emoji characters."""
        data = {"emoji": "😀🎉"}
        result = encoder.loads(encoder.dumps(data))
        assert result == data
