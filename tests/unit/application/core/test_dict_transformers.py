# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for dict_transformers common transformation utilities."""

from __future__ import annotations

from datetime import date

import pytest

from bioetl.application.core.dict_transformers import (
    aggregate_nested_lists,
    extract_list_field,
    flatten_nested_dict,
    normalize_string,
    parse_date_field,
    safe_extract,
    safe_float,
    safe_int,
    validate_smiles,
)


# ---------------------------------------------------------------------------
# flatten_nested_dict tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFlattenNestedDict:
    """Tests for flatten_nested_dict."""

    def test_basic_flattening(self):
        """Test basic dict flattening with prefix."""
        data = {"alogp": "3.5", "hba": 2}
        mapping = {"alogp": safe_float, "hba": safe_int}

        result = flatten_nested_dict(data, "property_", mapping)

        assert result == {"property_alogp": 3.5, "property_hba": 2}

    def test_none_data_returns_none_values(self):
        """Test that None data returns dict with None values for all keys."""
        mapping = {"alogp": safe_float, "hba": safe_int}

        result = flatten_nested_dict(None, "property_", mapping)

        assert result == {"property_alogp": None, "property_hba": None}

    def test_empty_dict_returns_none_values(self):
        """Test that empty dict returns dict with None values."""
        mapping = {"alogp": safe_float}

        result = flatten_nested_dict({}, "prefix_", mapping)

        assert result == {"prefix_alogp": None}

    def test_converter_none_passes_through(self):
        """Test that None converter passes values through unchanged."""
        data = {"name": "aspirin"}
        mapping = {"name": None}

        result = flatten_nested_dict(data, "drug_", mapping)

        assert result == {"drug_name": "aspirin"}

    def test_converter_with_none_value(self):
        """Test that converter is not applied when source value is None."""
        data = {"alogp": None}
        mapping = {"alogp": safe_float}

        result = flatten_nested_dict(data, "property_", mapping)

        assert result == {"property_alogp": None}

    def test_missing_key_returns_none(self):
        """Test that missing key in data returns None."""
        data = {"other_field": "value"}
        mapping = {"alogp": safe_float}

        result = flatten_nested_dict(data, "property_", mapping)

        assert result == {"property_alogp": None}

    def test_renames_parameter(self):
        """Test field renaming with the renames parameter."""
        data = {"molecule_chembl_id": "CHEMBL25"}
        mapping = {"molecule_chembl_id": None}
        renames = {"hierarchy_molecule_chembl_id": "hierarchy_child_chembl_id"}

        result = flatten_nested_dict(data, "hierarchy_", mapping, renames)

        assert "hierarchy_child_chembl_id" in result
        assert "hierarchy_molecule_chembl_id" not in result
        assert result["hierarchy_child_chembl_id"] == "CHEMBL25"

    def test_renames_non_matching_key_ignored(self):
        """Test that renames with non-matching keys are ignored."""
        data = {"id": "123"}
        mapping = {"id": None}
        renames = {"nonexistent_key": "new_key"}

        result = flatten_nested_dict(data, "prefix_", mapping, renames)

        assert result == {"prefix_id": "123"}

    def test_non_dict_data_returns_none_values(self):
        """Test that non-dict data returns None values."""
        mapping = {"field": None}

        result = flatten_nested_dict("not a dict", "prefix_", mapping)  # type: ignore[arg-type]

        assert result == {"prefix_field": None}


# ---------------------------------------------------------------------------
# extract_list_field tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractListField:
    """Tests for extract_list_field."""

    def test_basic_extraction(self):
        """Test basic field extraction from list of dicts."""
        items = [{"id": "1"}, {"id": "2"}, {"id": None}]

        result = extract_list_field(items, "id")

        assert result == ["1", "2"]

    def test_extraction_with_converter(self):
        """Test extraction with safe_int converter."""
        items = [{"id": "1"}, {"id": "2"}, {"id": "bad"}]

        result = extract_list_field(items, "id", safe_int)

        assert result == [1, 2]

    def test_none_items_returns_none(self):
        """Test that None input returns None."""
        assert extract_list_field(None, "id") is None

    def test_extract_list_field__list_returns_none__08a483cc(self):
        """Test that empty list returns None."""
        assert extract_list_field([], "id") is None

    def test_all_none_values_returns_none(self):
        """Test that all-None values returns None."""
        items = [{"id": None}, {"id": None}]

        assert extract_list_field(items, "id") is None

    def test_non_dict_items_skipped(self):
        """Test that non-dict items in the list are skipped."""
        items = [{"id": "1"}, "not a dict", {"id": "2"}]  # type: ignore[list-item]

        result = extract_list_field(items, "id")

        assert result == ["1", "2"]

    def test_missing_field_skipped(self):
        """Test that items without the target field are skipped."""
        items = [{"id": "1"}, {"name": "test"}, {"id": "2"}]

        result = extract_list_field(items, "id")

        assert result == ["1", "2"]

    def test_converter_returning_none_skips_value(self):
        """Test that converter returning None causes value to be skipped."""
        items = [{"val": "abc"}, {"val": "42"}]

        result = extract_list_field(items, "val", safe_int)

        assert result == [42]


# ---------------------------------------------------------------------------
# aggregate_nested_lists tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAggregateNestedLists:
    """Tests for aggregate_nested_lists."""

    def test_basic_aggregation(self):
        """Test basic aggregation of nested lists."""
        items = [
            {"synonyms": ["a", "b"]},
            {"synonyms": ["c", "a"]},
        ]

        result = aggregate_nested_lists(items, "synonyms")

        assert result == ["a", "b", "c"]

    def test_aggregation_without_dedup(self):
        """Test aggregation without deduplication."""
        items = [
            {"synonyms": ["a", "b"]},
            {"synonyms": ["a", "c"]},
        ]

        result = aggregate_nested_lists(items, "synonyms", deduplicate=False)

        assert result == ["a", "b", "a", "c"]

    def test_aggregate_nested_lists__items_returns_none__86a97e92(self):
        """Test that None input returns None."""
        assert aggregate_nested_lists(None, "synonyms") is None

    def test_aggregate_nested_lists__list_returns_none__97d6967f(self):
        """Test that empty list returns None."""
        assert aggregate_nested_lists([], "synonyms") is None

    def test_items_without_field_returns_none(self):
        """Test that items without the target field return None."""
        items = [{"other": "value"}]

        assert aggregate_nested_lists(items, "synonyms") is None

    def test_mixed_items_with_and_without_field(self):
        """Test aggregation where some items lack the field."""
        items = [
            {"synonyms": ["a", "b"]},
            {"other": "data"},
            {"synonyms": ["c"]},
        ]

        result = aggregate_nested_lists(items, "synonyms")

        assert result == ["a", "b", "c"]

    def test_non_list_nested_values_skipped(self):
        """Test that non-list nested values are skipped."""
        items = [
            {"synonyms": "not a list"},
            {"synonyms": ["a"]},
        ]

        result = aggregate_nested_lists(items, "synonyms")

        assert result == ["a"]

    def test_non_list_input_returns_none(self):
        """Test that non-list input returns None."""
        assert aggregate_nested_lists("not a list", "field") is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# normalize_string tests (delegates to domain)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeString:
    """Tests for normalize_string."""

    def test_strips_whitespace(self):
        """Test whitespace stripping."""
        assert normalize_string("  hello world  ") == "hello world"

    def test_empty_after_strip_returns_none(self):
        """Test that whitespace-only string returns None."""
        assert normalize_string("   ") is None

    def test_normalize_string__none_returns_none__9545bba9(self):
        """Test that None returns None."""
        assert normalize_string(None) is None

    def test_non_empty_string(self):
        """Test that non-empty string is preserved."""
        assert normalize_string("test") == "test"


# ---------------------------------------------------------------------------
# parse_date_field tests (delegates to domain)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseDateField:
    """Tests for parse_date_field."""

    def test_valid_iso_date(self):
        """Test parsing a valid ISO date."""
        result = parse_date_field("2024-01-15")

        assert result == date(2024, 1, 15)

    def test_custom_format(self):
        """Test parsing with a custom date format."""
        result = parse_date_field("15/01/2024", "%d/%m/%Y")

        assert result == date(2024, 1, 15)

    def test_invalid_date_returns_none(self):
        """Test that invalid date returns None."""
        assert parse_date_field("invalid") is None

    def test_parse_date_field__none_returns_none__25e96006(self):
        """Test that None returns None."""
        assert parse_date_field(None) is None

    def test_strips_whitespace_before_parse(self):
        """Test that whitespace is stripped before parsing."""
        result = parse_date_field("  2024-01-15  ")

        assert result == date(2024, 1, 15)


# ---------------------------------------------------------------------------
# validate_smiles tests (delegates to domain)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateSmiles:
    """Tests for validate_smiles."""

    def test_valid_smiles_ethanol(self):
        """Test valid SMILES for ethanol."""
        assert validate_smiles("CCO") is True

    def test_valid_smiles_benzene(self):
        """Test valid SMILES for benzene."""
        assert validate_smiles("C1=CC=CC=C1") is True

    def test_empty_string(self):
        """Test empty string returns False."""
        assert validate_smiles("") is False

    def test_none_returns_false(self):
        """Test None returns False."""
        assert validate_smiles(None) is False

    def test_spaces_invalid(self):
        """Test string with spaces is invalid."""
        assert validate_smiles("invalid smiles with spaces") is False


# ---------------------------------------------------------------------------
# safe_extract tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSafeExtract:
    """Tests for safe_extract."""

    def test_existing_key(self):
        """Test extraction of existing key."""
        record = {"name": "test", "value": 42}

        assert safe_extract(record, "name") == "test"

    def test_safe_extract__key_returns_none__f3ed0559(self):
        """Test missing key returns None by default."""
        record = {"name": "test"}

        assert safe_extract(record, "missing") is None

    def test_missing_key_with_default(self):
        """Test missing key returns provided default."""
        record = {"name": "test"}

        assert safe_extract(record, "missing", "default") == "default"

    def test_none_value_preserved(self):
        """Test that explicit None value is returned (not default)."""
        record = {"name": None}

        assert safe_extract(record, "name", "fallback") is None


# ---------------------------------------------------------------------------
# Re-exported safe_float / safe_int tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSafeFloatReExport:
    """Tests for re-exported safe_float."""

    def test_valid_string(self):
        """Test float conversion from string."""
        assert safe_float("3.14") == pytest.approx(3.14)

    def test_safe_float_re_export__none_returns_none__e1ed9bf3(self):
        """Test None returns None."""
        assert safe_float(None) is None

    def test_invalid_returns_none(self):
        """Test invalid input returns None."""
        assert safe_float("not a number") is None


@pytest.mark.unit
class TestSafeIntReExport:
    """Tests for re-exported safe_int."""

    def test_safe_int_re_export__valid_string__6bc710f6(self):
        """Test int conversion from string."""
        assert safe_int("42") == 42

    def test_safe_int_re_export__none_returns_none__69aef675(self):
        """Test None returns None."""
        assert safe_int(None) is None

    def test_safe_int_re_export__invalid_returns_none__5c083246(self):
        """Test invalid input returns None."""
        assert safe_int("not a number") is None
