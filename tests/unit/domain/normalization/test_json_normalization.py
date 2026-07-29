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
"""Tests for canonical JSON normalization."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.json import (
    canonicalize_json_string,
    deserialize_json_value,
    serialize_json_canonical,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_json_string,
    normalize_profile_json_string_strict,
)


pytestmark = pytest.mark.unit


class TestCanonicalJsonSerializer:
    """Test canonical JSON serialization functions."""

    def test_basic_serialization(self) -> None:
        """Test basic canonical serialization."""
        data = {"b": 2, "a": 1}
        result = serialize_json_canonical(data)
        assert result == '{"a":1,"b":2}'

    def test_nested_serialization(self) -> None:
        """Test nested structure serialization."""
        data = {
            "authors": ["Charlie", "Alice"],
            "metadata": {"year": 2023, "tags": ["bio", "chem"]},
        }
        result = serialize_json_canonical(data)
        # Array elements maintain original order, only dict keys are sorted
        expected = '{"authors":["Charlie","Alice"],"metadata":{"tags":["bio","chem"],"year":2023}}'
        assert result == expected

    def test_array_serialization(self) -> None:
        """Test array serialization."""
        data = [{"name": "Bob"}, {"name": "Alice"}]
        result = serialize_json_canonical(data)
        # Array elements maintain original order, only dict keys are sorted
        expected = '[{"name":"Bob"},{"name":"Alice"}]'
        assert result == expected

    def test_special_characters(self) -> None:
        """Test handling of special characters."""
        data = {"text": "Hello\nWorld", "emoji": "👋"}
        result = serialize_json_canonical(data)
        # Should handle special characters properly
        assert '"text"' in result
        assert '"emoji"' in result


class TestCanonicalizeJsonString:
    """Test JSON string canonicalization."""

    def test_key_reordering(self) -> None:
        """Test that keys are reordered canonically."""
        input_json = '{"year":2023,"authors":["Bob","Alice"]}'
        result = canonicalize_json_string(input_json)
        # Array elements maintain original order, only dict keys are sorted
        expected = '{"authors":["Bob","Alice"],"year":2023}'
        assert result == expected

    def test_json_string__whitespace_handling__eea8db3c(self) -> None:
        """Test whitespace stripping."""
        input_json = '  {"data":["test"]}  '
        result = canonicalize_json_string(input_json)
        expected = '{"data":["test"]}'
        assert result == expected

    def test_json_string__none_input__732a0fa4(self) -> None:
        """Test None input handling."""
        result = canonicalize_json_string(None)
        assert result is None

    def test_json_string__empty_string__d2e3bb08(self) -> None:
        """Test empty string handling."""
        result = canonicalize_json_string("   ")
        assert result is None

    def test_invalid_json(self) -> None:
        """Test invalid JSON handling in profile context."""
        # The raw function raises ValueError, but profile normalizer preserves invalid JSON
        # Test the profile-level behavior
        result = normalize_profile_json_string("invalid json")
        # Profile normalizer preserves invalid JSON as-is
        assert result == "invalid json"

    def test_invalid_json_raw_function(self) -> None:
        """Test that raw function raises ValueError for invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            canonicalize_json_string("invalid json")


class TestProfileJsonNormalization:
    """Test JSON normalization in profiles."""

    def test_profile_json_normalizer(self) -> None:
        """Test the profile JSON normalizer function."""
        # Test valid JSON
        input_json = '{"z":3,"a":1}'
        result = normalize_profile_json_string(input_json)
        expected = '{"a":1,"z":3}'
        assert result == expected

        # Test None
        assert normalize_profile_json_string(None) is None

        # Test non-string
        assert normalize_profile_json_string(123) == 123

        # Test invalid JSON (should be preserved)
        assert normalize_profile_json_string("not json") == "not json"

    def test_profile_strict_json_normalizer_fails_closed(self) -> None:
        """Strict JSON profile fields must collapse malformed payloads to None."""
        input_json = '{"z":3,"a":1}'
        result = normalize_profile_json_string_strict(input_json)
        expected = '{"a":1,"z":3}'
        assert result == expected

        assert normalize_profile_json_string_strict(None) is None
        assert normalize_profile_json_string_strict(123) == 123
        assert normalize_profile_json_string_strict("not json") is None


class TestJsonRoundtrip:
    """Test JSON serialization/deserialization roundtrips."""

    def test_roundtrip_consistency(self) -> None:
        """Test that serialize → deserialize → serialize is idempotent."""
        original = {"b": 2, "a": 1, "c": [3, 1]}

        # First serialization
        first = serialize_json_canonical(original)

        # Deserialize and serialize again
        parsed = deserialize_json_value(first)
        second = serialize_json_canonical(parsed)

        # Should be identical
        assert first == second

    def test_nested_roundtrip(self) -> None:
        """Test roundtrip with nested structures."""
        data = {"level1": {"level2": {"value": 42}, "array": [3, 1, 2]}}

        serialized = serialize_json_canonical(data)
        parsed = deserialize_json_value(serialized)
        reserialized = serialize_json_canonical(parsed)

        assert serialized == reserialized


class TestHashStability:
    """Test that canonical JSON ensures hash stability."""

    def test_hash_consistency(self) -> None:
        """Test that different key orders produce same hash."""
        json1 = '{"year":2023,"authors":["Alice","Bob"]}'
        json2 = '{"authors":["Alice","Bob"],"year":2023}'

        norm1 = canonicalize_json_string(json1)
        norm2 = canonicalize_json_string(json2)

        # Should be identical
        assert norm1 == norm2
        assert hash(norm1) == hash(norm2)

    def test_array_order_stability(self) -> None:
        """Test that array element order affects hash (as expected)."""
        json1 = '{"items":["a","b"]}'
        json2 = '{"items":["b","a"]}'

        norm1 = canonicalize_json_string(json1)
        norm2 = canonicalize_json_string(json2)

        # Should be different (semantic difference)
        assert norm1 != norm2
        assert hash(norm1) != hash(norm2)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unicode_handling(self) -> None:
        """Test Unicode character handling."""
        data = {"text": "Hello 世界", "emoji": "👋"}
        result = serialize_json_canonical(data)
        assert '"text"' in result
        assert '"emoji"' in result

    def test_numeric_edge_cases(self) -> None:
        """Test numeric edge cases."""
        data = {"zero": 0, "negative": -42, "float": 3.14159, "large": 1e10}
        result = serialize_json_canonical(data)
        assert '"zero":0' in result
        assert '"negative":-42' in result

    def test_boolean_handling(self) -> None:
        """Test boolean value handling."""
        data = {"flag1": True, "flag2": False}
        result = serialize_json_canonical(data)
        assert '"flag1":true' in result
        assert '"flag2":false' in result

    def test_null_handling(self) -> None:
        """Test null value handling."""
        data = {"value": None}
        result = serialize_json_canonical(data)
        assert '"value":null' in result
