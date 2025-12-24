"""Unit tests for transform_utils module.

Tests all utility functions for field extraction, transformation, and validation.
"""

from __future__ import annotations

from datetime import date

from bioetl.application.core.transform_utils import (
    aggregate_nested_list,
    build_empty_field_dict,
    extract_and_flatten_fields,
    extract_list_field,
    extract_nested_field_values,
    normalize_string_field,
    parse_date_field,
    safe_extract,
    safe_float,
    safe_int,
    validate_smiles,
)


class TestSafeExtract:
    """Tests for safe_extract function."""

    def test_extract_existing_key(self) -> None:
        record = {"name": "test", "value": 42}
        assert safe_extract(record, "name") == "test"
        assert safe_extract(record, "value") == 42

    def test_extract_missing_key_returns_default(self) -> None:
        record = {"name": "test"}
        assert safe_extract(record, "missing") is None
        assert safe_extract(record, "missing", "default") == "default"

    def test_extract_none_value_returns_default(self) -> None:
        record = {"name": None}
        assert safe_extract(record, "name") is None
        assert safe_extract(record, "name", "default") == "default"

    def test_strip_strings_by_default(self) -> None:
        record = {"name": "  test  "}
        assert safe_extract(record, "name") == "test"

    def test_strip_strings_disabled(self) -> None:
        record = {"name": "  test  "}
        assert safe_extract(record, "name", strip_strings=False) == "  test  "

    def test_empty_string_returns_default(self) -> None:
        record = {"name": "   "}
        assert safe_extract(record, "name") is None
        assert safe_extract(record, "name", "default") == "default"


class TestNormalizeStringField:
    """Tests for normalize_string_field function."""

    def test_none_returns_none(self) -> None:
        assert normalize_string_field(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert normalize_string_field("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert normalize_string_field("   ") is None

    def test_strips_whitespace(self) -> None:
        assert normalize_string_field("  hello  ") == "hello"

    def test_collapses_internal_spaces(self) -> None:
        assert normalize_string_field("hello   world") == "hello world"
        assert normalize_string_field("  hello   world  ") == "hello world"


class TestParseDateField:
    """Tests for parse_date_field function."""

    def test_parse_iso_format(self) -> None:
        result = parse_date_field("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_custom_format(self) -> None:
        result = parse_date_field("15/01/2024", fmt="%d/%m/%Y")
        assert result == date(2024, 1, 15)

    def test_parse_with_fallback_formats(self) -> None:
        result = parse_date_field(
            "Jan 15, 2024",
            fmt="%Y-%m-%d",
            fallback_formats=("%b %d, %Y",),
        )
        assert result == date(2024, 1, 15)

    def test_none_returns_none(self) -> None:
        assert parse_date_field(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_date_field("") is None

    def test_invalid_format_returns_none(self) -> None:
        assert parse_date_field("not a date") is None

    def test_strips_whitespace(self) -> None:
        result = parse_date_field("  2024-01-15  ")
        assert result == date(2024, 1, 15)


class TestValidateSmiles:
    """Tests for validate_smiles function."""

    def test_valid_simple_smiles(self) -> None:
        assert validate_smiles("CCO") is True  # Ethanol
        assert validate_smiles("C1=CC=CC=C1") is True  # Benzene
        assert validate_smiles("CC(=O)O") is True  # Acetic acid

    def test_valid_complex_smiles(self) -> None:
        assert validate_smiles("CC[C@H](C)[C@H]1NC(=O)C") is True

    def test_none_returns_false(self) -> None:
        assert validate_smiles(None) is False

    def test_empty_string_returns_false(self) -> None:
        assert validate_smiles("") is False

    def test_whitespace_only_returns_false(self) -> None:
        assert validate_smiles("   ") is False

    def test_invalid_characters_returns_false(self) -> None:
        assert validate_smiles("invalid smiles!") is False
        assert validate_smiles("CC O") is False  # Space not allowed


class TestExtractAndFlattenFields:
    """Tests for extract_and_flatten_fields function."""

    def test_basic_extraction(self) -> None:
        data = {"parent_id": "123", "name": "Test"}
        mappings: dict[str, tuple[str, None]] = {
            "output_parent_id": ("parent_id", None),
            "output_name": ("name", None),
        }
        result = extract_and_flatten_fields(data, mappings)
        assert result == {"output_parent_id": "123", "output_name": "Test"}

    def test_with_type_converter(self) -> None:
        data = {"value": "42", "ratio": "3.14"}
        mappings = {
            "int_value": ("value", safe_int),
            "float_ratio": ("ratio", safe_float),
        }
        result = extract_and_flatten_fields(data, mappings)
        assert result == {"int_value": 42, "float_ratio": 3.14}

    def test_none_data_returns_all_none(self) -> None:
        mappings: dict[str, tuple[str, None]] = {
            "field1": ("src1", None),
            "field2": ("src2", None),
        }
        result = extract_and_flatten_fields(None, mappings)
        assert result == {"field1": None, "field2": None}

    def test_empty_dict_returns_all_none(self) -> None:
        mappings: dict[str, tuple[str, None]] = {
            "field1": ("src1", None),
        }
        result = extract_and_flatten_fields({}, mappings)
        assert result == {"field1": None}

    def test_missing_field_returns_none(self) -> None:
        data = {"existing": "value"}
        mappings: dict[str, tuple[str, None]] = {
            "out_existing": ("existing", None),
            "out_missing": ("missing", None),
        }
        result = extract_and_flatten_fields(data, mappings)
        assert result == {"out_existing": "value", "out_missing": None}


class TestExtractListField:
    """Tests for extract_list_field function."""

    def test_basic_extraction(self) -> None:
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = extract_list_field(items, "id")
        assert result == [1, 2, 3]

    def test_with_converter(self) -> None:
        items = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        result = extract_list_field(items, "id", converter=safe_int)
        assert result == [1, 2, 3]

    def test_filters_none_by_default(self) -> None:
        items = [{"id": 1}, {"id": None}, {"id": 3}]
        result = extract_list_field(items, "id")
        assert result == [1, 3]

    def test_filter_none_disabled(self) -> None:
        items = [{"id": 1}, {"id": None}, {"id": 3}]
        result = extract_list_field(items, "id", filter_none=False)
        assert result == [1, None, 3]

    def test_none_items_returns_none(self) -> None:
        assert extract_list_field(None, "id") is None

    def test_empty_list_returns_none(self) -> None:
        assert extract_list_field([], "id") is None

    def test_all_none_values_returns_none(self) -> None:
        items = [{"id": None}, {"id": None}]
        assert extract_list_field(items, "id") is None

    def test_skips_non_dict_items(self) -> None:
        items = [{"id": 1}, "not a dict", {"id": 2}]  # type: ignore[list-item]
        result = extract_list_field(items, "id")
        assert result == [1, 2]


class TestAggregateNestedList:
    """Tests for aggregate_nested_list function."""

    def test_basic_aggregation(self) -> None:
        items = [
            {"synonyms": ["a", "b"]},
            {"synonyms": ["c"]},
        ]
        result = aggregate_nested_list(items, "synonyms")
        assert result == ["a", "b", "c"]

    def test_skips_none_and_non_list(self) -> None:
        items = [
            {"synonyms": ["a"]},
            {"synonyms": None},
            {"synonyms": "not a list"},
            {"synonyms": ["b"]},
        ]
        result = aggregate_nested_list(items, "synonyms")
        assert result == ["a", "b"]

    def test_none_items_returns_none(self) -> None:
        assert aggregate_nested_list(None, "synonyms") is None

    def test_empty_list_returns_none(self) -> None:
        assert aggregate_nested_list([], "synonyms") is None

    def test_all_empty_nested_returns_none(self) -> None:
        items = [{"synonyms": []}, {"synonyms": []}]
        assert aggregate_nested_list(items, "synonyms") is None


class TestExtractNestedFieldValues:
    """Tests for extract_nested_field_values function."""

    def test_basic_extraction(self) -> None:
        items = [
            {"classes": [{"id": 1}, {"id": 2}]},
            {"classes": [{"id": 3}]},
        ]
        result = extract_nested_field_values(items, "classes", "id")
        assert result == [1, 2, 3]

    def test_with_converter(self) -> None:
        items = [
            {"classes": [{"id": "1"}, {"id": "2"}]},
        ]
        result = extract_nested_field_values(
            items, "classes", "id", converter=safe_int
        )
        assert result == [1, 2]

    def test_skips_none_values(self) -> None:
        items = [
            {"classes": [{"id": 1}, {"id": None}, {"id": 2}]},
        ]
        result = extract_nested_field_values(items, "classes", "id")
        assert result == [1, 2]

    def test_none_items_returns_none(self) -> None:
        assert extract_nested_field_values(None, "classes", "id") is None

    def test_empty_nested_returns_none(self) -> None:
        items = [{"classes": []}]
        assert extract_nested_field_values(items, "classes", "id") is None

    def test_skips_non_dict_nested_items(self) -> None:
        items = [
            {"classes": [{"id": 1}, "not a dict", {"id": 2}]},
        ]
        result = extract_nested_field_values(items, "classes", "id")
        assert result == [1, 2]


class TestBuildEmptyFieldDict:
    """Tests for build_empty_field_dict function."""

    def test_creates_dict_with_none_values(self) -> None:
        fields = ["id", "name", "value"]
        result = build_empty_field_dict(fields)
        assert result == {"id": None, "name": None, "value": None}

    def test_empty_list(self) -> None:
        assert build_empty_field_dict([]) == {}


class TestSafeFloatAndSafeInt:
    """Tests for re-exported safe_float and safe_int."""

    def test_safe_float_valid(self) -> None:
        assert safe_float("3.14") == 3.14
        assert safe_float(42) == 42.0

    def test_safe_float_none(self) -> None:
        assert safe_float(None) is None

    def test_safe_float_invalid(self) -> None:
        assert safe_float("not a number") is None

    def test_safe_int_valid(self) -> None:
        assert safe_int("42") == 42
        assert safe_int(3.7) == 3

    def test_safe_int_none(self) -> None:
        assert safe_int(None) is None

    def test_safe_int_invalid(self) -> None:
        assert safe_int("not a number") is None
