"""Tests for metadata_builder_composite_helpers.py.

Targets uncovered lines: 22, 26-27, 30, 40, 44-45, 48, 66, 76-82.
"""

from __future__ import annotations

import pytest

from bioetl.infrastructure.storage.metadata_builder_composite_helpers import (
    build_composite_output_ext,
    parse_composite_list,
    parse_composite_status,
)


@pytest.mark.unit
class TestParseCompositeList:
    """Tests for parse_composite_list."""

    def test_list_input_returns_strings(self) -> None:
        """Line 22: list input is converted to list[str]."""
        result = parse_composite_list(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_list_with_non_string_items(self) -> None:
        """Line 22: non-string items in list are coerced to str."""
        result = parse_composite_list([1, 2, 3])
        assert result == ["1", "2", "3"]

    def test_string_input_valid_list(self) -> None:
        """Lines 24-29: valid stringified list is parsed."""
        result = parse_composite_list("['chembl', 'pubchem']")
        assert result == ["chembl", "pubchem"]

    def test_string_input_invalid_syntax(self) -> None:
        """Lines 26-27: invalid syntax returns empty list."""
        result = parse_composite_list("not a list")
        assert result == []

    def test_string_input_not_a_list(self) -> None:
        """Line 30: stringified dict (not a list) returns empty list."""
        result = parse_composite_list("{'key': 'val'}")
        assert result == []

    def test_none_input_returns_empty(self) -> None:
        """Line 30: None returns empty list."""
        result = parse_composite_list(None)
        assert result == []

    def test_integer_input_returns_empty(self) -> None:
        """Line 30: int input returns empty list."""
        result = parse_composite_list(42)
        assert result == []

    def test_empty_list_input(self) -> None:
        """Line 22: empty list returns empty list."""
        result = parse_composite_list([])
        assert result == []

    def test_string_input_empty_list(self) -> None:
        """Stringified empty list returns empty list."""
        result = parse_composite_list("[]")
        assert result == []

    def test_string_with_syntax_error(self) -> None:
        """Lines 26-27: SyntaxError in literal_eval returns empty list."""
        result = parse_composite_list("[invalid syntax}")
        assert result == []


@pytest.mark.unit
class TestParseCompositeStatus:
    """Tests for parse_composite_status."""

    def test_dict_input_returns_str_str(self) -> None:
        """Line 40: dict input is converted to dict[str, str]."""
        result = parse_composite_status({"chembl": "enriched", "pubchem": "partial"})
        assert result == {"chembl": "enriched", "pubchem": "partial"}

    def test_dict_with_non_string_keys_values(self) -> None:
        """Line 40: non-string keys/values coerced to str."""
        result = parse_composite_status({1: True, 2: False})
        assert result == {"1": "True", "2": "False"}

    def test_string_input_valid_dict(self) -> None:
        """Lines 42-47: valid stringified dict is parsed."""
        result = parse_composite_status("{'provider': 'ok'}")
        assert result == {"provider": "ok"}

    def test_string_input_invalid_syntax(self) -> None:
        """Lines 44-45: invalid syntax returns empty dict."""
        result = parse_composite_status("not a dict")
        assert result == {}

    def test_string_input_not_a_dict(self) -> None:
        """Line 48: stringified list (not a dict) returns empty dict."""
        result = parse_composite_status("['a', 'b']")
        assert result == {}

    def test_none_input_returns_empty(self) -> None:
        """Line 48: None returns empty dict."""
        result = parse_composite_status(None)
        assert result == {}

    def test_integer_input_returns_empty(self) -> None:
        """Line 48: int returns empty dict."""
        result = parse_composite_status(42)
        assert result == {}

    def test_empty_dict_input(self) -> None:
        """Line 40: empty dict returns empty dict."""
        result = parse_composite_status({})
        assert result == {}

    def test_string_with_syntax_error(self) -> None:
        """SyntaxError in literal_eval returns empty dict."""
        result = parse_composite_status("{invalid}")
        assert result == {}


@pytest.mark.unit
class TestBuildCompositeOutputExt:
    """Tests for build_composite_output_ext."""

    def test_empty_records_returns_none(self) -> None:
        """Line 66: empty records returns None."""
        result = build_composite_output_ext([])
        assert result is None

    def test_records_without_composite_fields_returns_none(self) -> None:
        """Lines 69-72: records with no composite/lineage fields return None."""
        records = [{"activity_id": "CHEMBL1", "value": 5.0}]
        result = build_composite_output_ext(records)
        assert result is None

    def test_records_with_composite_prefix_field(self) -> None:
        """Line 69: _composite_ prefixed field triggers CompositeOutputExt."""
        records = [{"_composite_run_id": "run-123", "activity_id": "CHEMBL1"}]
        result = build_composite_output_ext(records)
        assert result is not None
        assert result.composite_run_id == "run-123"

    def test_records_with_source_providers_field(self) -> None:
        """Line 70: _source_providers triggers CompositeOutputExt."""
        records = [
            {
                "_source_providers": ["chembl", "pubchem"],
                "activity_id": "CHEMBL1",
            }
        ]
        result = build_composite_output_ext(records)
        assert result is not None
        assert result.source_providers == ["chembl", "pubchem"]

    def test_records_with_enrichment_status_field(self) -> None:
        """Line 70: _enrichment_status triggers CompositeOutputExt."""
        records = [
            {
                "_enrichment_status": {"chembl": "ok"},
                "activity_id": "CHEMBL1",
            }
        ]
        result = build_composite_output_ext(records)
        assert result is not None
        assert result.enrichment_status == {"chembl": "ok"}

    def test_lineage_created_at_iso_string(self) -> None:
        """Lines 76-80: lineage_created_at parsed from ISO string."""
        records = [
            {
                "_source_providers": ["chembl"],
                "_lineage_created_at": "2025-01-15T10:00:00",
            }
        ]
        result = build_composite_output_ext(records)
        assert result is not None
        assert result.lineage_created_at is not None
        assert result.lineage_created_at.year == 2025

    def test_lineage_created_at_invalid_string(self) -> None:
        """Lines 79-80: invalid ISO string results in None lineage_created_at."""
        records = [
            {
                "_source_providers": ["chembl"],
                "_lineage_created_at": "not-a-date",
            }
        ]
        result = build_composite_output_ext(records)
        assert result is not None
        assert result.lineage_created_at is None

    def test_lineage_created_at_missing(self) -> None:
        """No _lineage_created_at: lineage_created_at is None."""
        records = [{"_source_providers": ["chembl"]}]
        result = build_composite_output_ext(records)
        assert result is not None
        assert result.lineage_created_at is None

    def test_composite_run_id_none_when_absent(self) -> None:
        """Lines 83-86: composite_run_id is None when not present."""
        records = [{"_source_providers": ["chembl"]}]
        result = build_composite_output_ext(records)
        assert result is not None
        assert result.composite_run_id is None

    def test_schema_validation_disabled_by_default(self) -> None:
        """Lines 91-95: schema_validation has enabled=False, strict=None, status='not_run'."""
        records = [{"_source_providers": ["chembl"]}]
        result = build_composite_output_ext(records)
        assert result is not None
        assert result.schema_validation.enabled is False
        assert result.schema_validation.strict is None
        assert result.schema_validation.status == "not_run"

    def test_source_providers_as_stringified_list(self) -> None:
        """parse_composite_list called with stringified list."""
        records = [{"_source_providers": "['chembl', 'pubchem']"}]
        result = build_composite_output_ext(records)
        assert result is not None
        assert result.source_providers == ["chembl", "pubchem"]

    def test_enrichment_status_as_stringified_dict(self) -> None:
        """parse_composite_status called with stringified dict."""
        records = [{"_enrichment_status": "{'chembl': 'enriched'}"}]
        result = build_composite_output_ext(records)
        assert result is not None
        assert result.enrichment_status == {"chembl": "enriched"}
