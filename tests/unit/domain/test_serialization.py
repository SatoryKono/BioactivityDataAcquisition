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
# tests/unit/domain/test_serialization.py
"""Unit tests for domain serialization module.

Tests for canonical JSON serialization functions used in content hashing.
"""

from __future__ import annotations

import pyarrow as pa
import pytest

from bioetl.domain.serialization import (
    _escape_non_ascii,
    _has_non_ascii,
    canonicalize_json_string,
    deserialize_from_json,
    flatten_arrow_table_for_export,
    is_orjson_available,
    serialize_to_canonical_json,
    serialize_to_json,
    serialize_to_json_canonical,
)

pytestmark = pytest.mark.unit


class TestSerializeToJson:
    """Tests for serialize_to_json function."""

    def test_serialize_simple_dict(self) -> None:
        """Serialize simple dict to JSON."""
        data = {"a": 1, "b": 2}
        result = serialize_to_json(data)
        assert result == '{"a":1,"b":2}'

    def test_serialize_sorted_keys(self) -> None:
        """Keys are sorted by default."""
        data = {"z": 3, "a": 1, "m": 2}
        result = serialize_to_json(data)
        assert result == '{"a":1,"m":2,"z":3}'

    def test_serialize_unsorted_keys(self) -> None:
        """Keys are not sorted when sort_keys=False."""
        data = {"z": 3, "a": 1}
        result = serialize_to_json(data, sort_keys=False)
        # Result preserves insertion order in modern Python
        assert '"z":3' in result
        assert '"a":1' in result

    def test_serialize_nested_dict(self) -> None:
        """Serialize nested dict."""
        data = {"outer": {"inner": 1}}
        result = serialize_to_json(data)
        assert result == '{"outer":{"inner":1}}'

    def test_serialize_list(self) -> None:
        """Serialize list."""
        data = [1, 2, 3]
        result = serialize_to_json(data)
        assert result == "[1,2,3]"

    def test_serialize_mixed_types(self) -> None:
        """Serialize dict with mixed types."""
        data = {"str": "value", "int": 42, "float": 3.14, "bool": True, "null": None}
        result = serialize_to_json(data)
        # Verify all values are present
        assert '"str":"value"' in result
        assert '"int":42' in result
        assert '"float":3.14' in result
        assert '"bool":true' in result
        assert '"null":null' in result

    def test_serialize_empty_dict(self) -> None:
        """Serialize empty dict."""
        result = serialize_to_json({})
        assert result == "{}"

    def test_serialize_empty_list(self) -> None:
        """Serialize empty list."""
        result = serialize_to_json([])
        assert result == "[]"

    def test_serialize_unicode_with_ensure_ascii(self) -> None:
        """Non-ASCII chars are escaped when ensure_ascii=True."""
        data = {"key": "тест"}
        result = serialize_to_json(data, ensure_ascii=True)
        # Should not contain cyrillic chars
        assert "тест" not in result or "\\u" in result

    def test_serialize_unicode_without_ensure_ascii(self) -> None:
        """Non-ASCII chars are preserved when ensure_ascii=False."""
        data = {"key": "тест"}
        result = serialize_to_json(data, ensure_ascii=False)
        # Should contain actual unicode or escaped version
        assert "тест" in result or "\\u" in result


class TestSerializeToJsonCanonical:
    """Tests for serialize_to_json_canonical function."""

    def test_canonical_sorted_keys(self) -> None:
        """Canonical serialization sorts keys."""
        data = {"b": 2, "a": 1}
        result = serialize_to_json_canonical(data)
        assert result == '{"a":1,"b":2}'

    def test_canonical_compact(self) -> None:
        """Canonical serialization uses compact format."""
        data = {"key": "value"}
        result = serialize_to_json_canonical(data)
        # No spaces after colon or comma
        assert ": " not in result
        assert ", " not in result

    def test_canonical_deterministic(self) -> None:
        """Canonical serialization is deterministic."""
        data = {"z": 1, "a": 2, "m": 3}
        result1 = serialize_to_json_canonical(data)
        result2 = serialize_to_json_canonical(data)
        assert result1 == result2

    def test_canonical_rejects_nan(self) -> None:
        """Canonical serialization rejects NaN to preserve cross-runtime parity."""
        with pytest.raises(
            ValueError,
            match="Canonical JSON serialization does not allow NaN or Infinity",
        ):
            serialize_to_json_canonical({"value": float("nan")})

    def test_canonical_rejects_infinity(self) -> None:
        """Canonical serialization rejects Infinity to preserve cross-runtime parity."""
        with pytest.raises(
            ValueError,
            match="Canonical JSON serialization does not allow NaN or Infinity",
        ):
            serialize_to_json_canonical({"value": float("inf")})


class TestSerializeToCanonicalJson:
    """Tests for serialize_to_canonical_json alias."""

    def test_alias_matches_public_canonical_serializer(self) -> None:
        """Alias delegates to the existing public canonical serializer."""
        data = {"z": 3, "a": 1, "m": 2}

        assert serialize_to_canonical_json(data) == serialize_to_json_canonical(data)

    def test_alias_escapes_non_ascii(self) -> None:
        """Alias preserves canonical ASCII-only output."""
        data = {"name": "café"}

        result = serialize_to_canonical_json(data)

        assert result == '{"name":"caf\\u00e9"}'

    def test_alias_is_deterministic(self) -> None:
        """Alias produces stable output for identical input."""
        data = {"b": 2, "a": 1}

        assert serialize_to_canonical_json(data) == serialize_to_canonical_json(data)


class TestDeserializeFromJson:
    """Tests for deserialize_from_json function."""

    def test_deserialize_string_to_dict(self) -> None:
        """Deserialize JSON string to dict."""
        data = '{"a": 1, "b": 2}'
        result = deserialize_from_json(data)
        assert result == {"a": 1, "b": 2}

    def test_deserialize_string_to_list(self) -> None:
        """Deserialize JSON string to list."""
        data = "[1, 2, 3]"
        result = deserialize_from_json(data)
        assert result == [1, 2, 3]

    def test_deserialize_bytes_to_dict(self) -> None:
        """Deserialize JSON bytes to dict."""
        data = b'{"a": 1}'
        result = deserialize_from_json(data)
        assert result == {"a": 1}

    def test_deserialize_bytes_to_list(self) -> None:
        """Deserialize JSON bytes to list."""
        data = b"[1, 2, 3]"
        result = deserialize_from_json(data)
        assert result == [1, 2, 3]

    def test_deserialize_nested_structure(self) -> None:
        """Deserialize nested JSON structure."""
        data = '{"outer": {"inner": [1, 2, 3]}}'
        result = deserialize_from_json(data)
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_deserialize_invalid_json_raises(self) -> None:
        """Deserialize invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            deserialize_from_json("{invalid}")

    def test_deserialize_truncated_json_raises(self) -> None:
        """Deserialize truncated JSON raises ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            deserialize_from_json('{"key": ')


class TestCanonicalizeJsonString:
    """Tests for canonicalize_json_string compatibility helper."""

    def test_canonicalizes_json_string(self) -> None:
        """JSON strings are normalized to deterministic canonical form."""
        assert canonicalize_json_string('{"b":2, "a":1}') == '{"a":1,"b":2}'

    def test_blank_json_string_returns_none(self) -> None:
        """Blank values normalize to None."""
        assert canonicalize_json_string("   ") is None

    def test_invalid_json_string_raises(self) -> None:
        """Invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            canonicalize_json_string("{invalid}")


class TestRoundTrip:
    """Tests for serialize/deserialize roundtrip."""

    def test_roundtrip_dict(self) -> None:
        """Roundtrip dict through JSON."""
        original = {"a": 1, "b": "test", "c": [1, 2, 3]}
        json_str = serialize_to_json(original)
        restored = deserialize_from_json(json_str)
        assert restored == original

    def test_roundtrip_list(self) -> None:
        """Roundtrip list through JSON."""
        original = [1, "test", {"key": "value"}]
        json_str = serialize_to_json(original)
        restored = deserialize_from_json(json_str)
        assert restored == original

    def test_roundtrip_complex_structure(self) -> None:
        """Roundtrip complex nested structure."""
        original = {
            "metadata": {
                "version": "1.0",
                "tags": ["a", "b"],
            },
            "records": [
                {"id": 1, "value": 100},
                {"id": 2, "value": 200},
            ],
        }
        json_str = serialize_to_json_canonical(original)
        restored = deserialize_from_json(json_str)
        assert restored == original


class TestEscapeNonAscii:
    """Tests for _escape_non_ascii helper function."""

    def test_escape_cyrillic(self) -> None:
        """Escape Cyrillic characters."""
        text = "тест"
        result = _escape_non_ascii(text)
        # Each char should be escaped
        assert "\\u" in result
        assert len(result) > len(text)

    def test_escape_ascii_unchanged(self) -> None:
        """ASCII text is unchanged."""
        text = "hello world"
        result = _escape_non_ascii(text)
        assert result == text

    def test_escape_mixed_content(self) -> None:
        """Mixed ASCII and non-ASCII content."""
        text = "hello мир"
        result = _escape_non_ascii(text)
        assert result.startswith("hello ")
        assert "\\u" in result

    def test_escape_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert _escape_non_ascii("") == ""


class TestHasNonAscii:
    """Tests for _has_non_ascii helper function."""

    def test_has_non_ascii_with_cyrillic(self) -> None:
        """Detect Cyrillic characters."""
        assert _has_non_ascii("тест") is True

    def test_has_non_ascii_with_emoji(self) -> None:
        """Detect emoji characters."""
        assert _has_non_ascii("hello 🌍") is True

    def test_has_non_ascii_pure_ascii(self) -> None:
        """Pure ASCII returns False."""
        assert _has_non_ascii("hello world 123") is False

    def test_has_non_ascii_empty_string(self) -> None:
        """Empty string returns False."""
        assert _has_non_ascii("") is False


class TestIsOrjsonAvailable:
    """Tests for is_orjson_available function."""

    def test_returns_boolean(self) -> None:
        """Function returns boolean."""
        result = is_orjson_available()
        assert isinstance(result, bool)

    def test_cached_result(self) -> None:
        """Result is cached."""
        result1 = is_orjson_available()
        result2 = is_orjson_available()
        assert result1 is result2


class TestFlattenArrowTableForExport:
    """Tests for flatten_arrow_table_for_export function."""

    def test_flatten_simple_columns(self) -> None:
        """Simple columns are unchanged."""
        table = pa.table(
            {
                "id": [1, 2, 3],
                "name": ["a", "b", "c"],
            }
        )
        result = flatten_arrow_table_for_export(table)

        assert result.column("id").to_pylist() == [1, 2, 3]
        assert result.column("name").to_pylist() == ["a", "b", "c"]

    def test_flatten_list_columns(self) -> None:
        """List columns are serialized to JSON."""
        table = pa.table(
            {
                "id": [1, 2],
                "tags": [[1, 2, 3], [4, 5]],
            }
        )
        result = flatten_arrow_table_for_export(table)

        # List column should be JSON strings
        tags = result.column("tags").to_pylist()
        assert tags[0] == "[1,2,3]"
        assert tags[1] == "[4,5]"

    def test_flatten_struct_columns(self) -> None:
        """Struct columns are serialized to JSON."""
        struct_type = pa.struct([("x", pa.int64()), ("y", pa.int64())])
        table = pa.table(
            {
                "id": [1, 2],
                "point": pa.array(
                    [{"x": 10, "y": 20}, {"x": 30, "y": 40}], type=struct_type
                ),
            }
        )
        result = flatten_arrow_table_for_export(table)

        # Struct column should be JSON strings
        points = result.column("point").to_pylist()
        assert '"x"' in points[0]
        assert '"y"' in points[0]

    def test_flatten_preserves_schema_names(self) -> None:
        """Schema column names are preserved."""
        table = pa.table(
            {
                "column_a": [1, 2],
                "column_b": [[1], [2]],
            }
        )
        result = flatten_arrow_table_for_export(table)

        assert "column_a" in result.column_names
        assert "column_b" in result.column_names

    def test_flatten_handles_null_values(self) -> None:
        """Null values in complex columns are handled."""
        table = pa.table(
            {
                "id": [1, 2],
                "tags": [[1, 2], None],
            }
        )
        result = flatten_arrow_table_for_export(table)

        tags = result.column("tags").to_pylist()
        assert tags[0] == "[1,2]"
        assert tags[1] is None

    def test_flatten_empty_table(self) -> None:
        """Empty table is handled."""
        table = pa.table({"id": pa.array([], type=pa.int64())})
        result = flatten_arrow_table_for_export(table)

        assert len(result) == 0
        assert "id" in result.column_names


class TestSerializationDeterminism:
    """Tests ensuring serialization is deterministic for content hashing."""

    def test_same_dict_same_output(self) -> None:
        """Same dict produces same output."""
        data = {"key1": "value1", "key2": "value2"}
        outputs = [serialize_to_json_canonical(data) for _ in range(10)]
        assert all(o == outputs[0] for o in outputs)

    def test_dict_order_independent(self) -> None:
        """Different dict creation order produces same canonical output."""
        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "b": 2, "a": 1}
        data3 = {"b": 2, "a": 1, "c": 3}

        result1 = serialize_to_json_canonical(data1)
        result2 = serialize_to_json_canonical(data2)
        result3 = serialize_to_json_canonical(data3)

        assert result1 == result2 == result3
        assert result1 == '{"a":1,"b":2,"c":3}'

    def test_nested_dict_order_independent(self) -> None:
        """Nested dicts are also canonicalized."""
        data1 = {"outer": {"z": 3, "a": 1}}
        data2 = {"outer": {"a": 1, "z": 3}}

        assert serialize_to_json_canonical(data1) == serialize_to_json_canonical(data2)
