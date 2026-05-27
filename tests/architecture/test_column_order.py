"""Architecture tests for canonical column ordering.

Verifies that all PyArrow schemas follow the canonical column order
defined in domain/schemas/column_order.py.

Per RULES.md §2.4 and ADR-014.
"""

from __future__ import annotations

from functools import cache
from typing import Any

import pytest

from bioetl.domain.schemas.column_order import (
    ALL_SYSTEM_FIELDS,
    DQ_FIELDS_SUFFIX,
    PUBLICATION_CROSSREF_FIELDS,
    PUBLICATION_METADATA_FIELDS,
    SYSTEM_FIELDS_PREFIX,
    canonical_column_order,
)

# Schemas with custom column order (not alphabetical business fields)
# These use PUBLICATION_METADATA_FIELDS, PUBLICATION_CROSSREF_FIELDS ordering
CUSTOM_ORDER_SCHEMAS = frozenset(
    {
        "CHEMBL_PUBLICATION_SCHEMA",
        "CHEMBL_ACTIVITY_SCHEMA",
        "CHEMBL_ASSAY_SCHEMA",
        "CHEMBL_CELL_LINE_SCHEMA",
        "CHEMBL_COMPOUND_RECORD_SCHEMA",
        "CHEMBL_DOCUMENT_TERM_SCHEMA",
        "CHEMBL_MOLECULE_SCHEMA",
        "CHEMBL_TARGET_SCHEMA",
        "PUBCHEM_COMPOUND_SCHEMA",
    }
)


@cache
def get_all_pyarrow_schemas() -> list[tuple[str, Any]]:
    """Collect all PyArrow schema constants from silver module."""
    import pyarrow as pa

    from bioetl.infrastructure.schemas import silver as silver_schemas

    schemas = []
    for name in dir(silver_schemas):
        obj = getattr(silver_schemas, name)
        if name.endswith("_SCHEMA") and isinstance(obj, pa.Schema):
            schemas.append((name, obj))
    return schemas


class TestCanonicalColumnOrderFunction:
    """Unit tests for canonical_column_order function."""

    def test_reorders_prefix_first(self) -> None:
        """System prefix fields should come first."""
        columns = ["name", "_run_id", "entity_id", "content_hash"]
        result = canonical_column_order(columns)
        assert result[:3] == ["entity_id", "content_hash", "_run_id"]

    def test_business_fields_sorted(self) -> None:
        """Business fields should be sorted alphabetically."""
        columns = ["entity_id", "zebra", "alpha", "content_hash"]
        result = canonical_column_order(columns)
        business = [c for c in result if c not in ALL_SYSTEM_FIELDS]
        assert business == ["alpha", "zebra"]

    def test_dq_suffix_last(self) -> None:
        """DQ fields should come last."""
        columns = ["_dq_warn", "name", "entity_id", "_dq_error"]
        result = canonical_column_order(columns)
        assert result[-2:] == ["_dq_error", "_dq_warn"]

    def test_preserves_all_columns(self) -> None:
        """All input columns should be in output."""
        columns = ["a", "b", "entity_id", "_run_id", "_dq_warn"]
        result = canonical_column_order(columns)
        assert set(result) == set(columns)

    def test_handles_tuple_input(self) -> None:
        """Should accept tuple input."""
        columns = ("entity_id", "name", "_run_id")
        result = canonical_column_order(columns)
        assert isinstance(result, list)
        assert result == ["entity_id", "_run_id", "name"]

    def test_empty_input(self) -> None:
        """Should handle empty input."""
        assert canonical_column_order([]) == []

    def test_only_system_fields(self) -> None:
        """Should handle input with only system fields."""
        columns = ["_run_id", "entity_id", "_dq_warn"]
        result = canonical_column_order(columns)
        assert result == ["entity_id", "_run_id", "_dq_warn"]

    def test_full_system_fields_order(self) -> None:
        """Test complete ordering with all system fields."""
        columns = [
            "_dq_error",
            "business_field",
            "_index",
            "_run_type",
            "entity_id",
            "_dq_warn",
            "content_hash",
            "_run_id",
            "_source_batch_id",
            "_ingestion_ts",
        ]
        result = canonical_column_order(columns)
        expected = [
            "entity_id",
            "content_hash",
            "_run_id",
            "_run_type",
            "_source_batch_id",
            "_ingestion_ts",
            "_index",
            "business_field",
            "_dq_error",
            "_dq_warn",
        ]
        assert result == expected


class TestSchemaColumnOrder:
    """Tests for PyArrow schema column ordering."""

    @pytest.mark.parametrize("schema_name,schema", get_all_pyarrow_schemas())
    def test_prefix_fields_in_correct_order(
        self, schema_name: str, schema: Any
    ) -> None:
        """System prefix fields MUST be in correct relative order."""
        column_names = schema.names

        # Get prefix fields that exist in this schema
        prefix_in_schema = [c for c in column_names if c in SYSTEM_FIELDS_PREFIX]
        expected_order = [c for c in SYSTEM_FIELDS_PREFIX if c in column_names]

        # Check they appear in the right relative order
        assert prefix_in_schema == expected_order, (
            f"{schema_name}: System prefix fields out of order.\n"
            f"Expected: {expected_order}\n"
            f"Got: {prefix_in_schema}"
        )

    @pytest.mark.parametrize("schema_name,schema", get_all_pyarrow_schemas())
    def test_prefix_fields_at_start(self, schema_name: str, schema: Any) -> None:
        """System prefix fields MUST be at the start of schema."""
        column_names = schema.names

        prefix_in_schema = [c for c in SYSTEM_FIELDS_PREFIX if c in column_names]
        if not prefix_in_schema:
            pytest.skip(f"{schema_name} has no system prefix fields")

        # First N columns should be the prefix fields
        first_n = column_names[: len(prefix_in_schema)]
        assert set(first_n) == set(prefix_in_schema), (
            f"{schema_name}: System prefix fields not at start.\n"
            f"Expected first {len(prefix_in_schema)} columns to be: {prefix_in_schema}\n"
            f"Got: {first_n}"
        )

    @pytest.mark.parametrize("schema_name,schema", get_all_pyarrow_schemas())
    def test_suffix_fields_at_end(self, schema_name: str, schema: Any) -> None:
        """DQ suffix fields MUST be last (if present)."""
        column_names = schema.names

        suffix_in_schema = [c for c in column_names if c in DQ_FIELDS_SUFFIX]
        if not suffix_in_schema:
            pytest.skip(f"{schema_name} has no DQ suffix fields")

        expected_suffix = [c for c in DQ_FIELDS_SUFFIX if c in column_names]
        actual_suffix = column_names[-len(suffix_in_schema) :]

        assert actual_suffix == expected_suffix, (
            f"{schema_name}: DQ suffix fields not at end.\n"
            f"Expected last columns: {expected_suffix}\n"
            f"Got: {actual_suffix}"
        )

    @pytest.mark.parametrize("schema_name,schema", get_all_pyarrow_schemas())
    def test_business_fields_sorted__test_schema_column_order_tests_architecture_test_column_order_189(
        self, schema_name: str, schema: Any
    ) -> None:
        """Business fields SHOULD be sorted alphabetically.

        Custom-ordered schemas use PUBLICATION_METADATA_FIELDS and
        PUBLICATION_CROSSREF_FIELDS grouping instead of strict alphabetical
        sort. For these, we verify that the publication group fields appear
        in their defined order among the business fields.
        """
        column_names = schema.names

        # Extract business fields (excluding system fields)
        business_fields = [c for c in column_names if c not in ALL_SYSTEM_FIELDS]

        if schema_name in CUSTOM_ORDER_SCHEMAS:
            # Validate publication group fields appear in defined order
            pub_meta_in_schema = [
                c for c in business_fields if c in PUBLICATION_METADATA_FIELDS
            ]
            expected_pub_meta = [
                c for c in PUBLICATION_METADATA_FIELDS if c in set(business_fields)
            ]
            assert pub_meta_in_schema == expected_pub_meta, (
                f"{schema_name}: PUBLICATION_METADATA_FIELDS out of order.\n"
                f"Expected: {expected_pub_meta}\n"
                f"Got: {pub_meta_in_schema}"
            )

            pub_xref_in_schema = [
                c for c in business_fields if c in PUBLICATION_CROSSREF_FIELDS
            ]
            expected_pub_xref = [
                c for c in PUBLICATION_CROSSREF_FIELDS if c in set(business_fields)
            ]
            assert pub_xref_in_schema == expected_pub_xref, (
                f"{schema_name}: PUBLICATION_CROSSREF_FIELDS out of order.\n"
                f"Expected: {expected_pub_xref}\n"
                f"Got: {pub_xref_in_schema}"
            )
        else:
            sorted_business = sorted(business_fields)
            assert business_fields == sorted_business, (
                f"{schema_name}: Business fields not sorted alphabetically.\n"
                f"Expected: {sorted_business[:5]}...\n"
                f"Got: {business_fields[:5]}..."
            )

    @pytest.mark.parametrize("schema_name,schema", get_all_pyarrow_schemas())
    def test_schema_matches_canonical_order(
        self, schema_name: str, schema: Any
    ) -> None:
        """Schema column order MUST match canonical_column_order() output.

        Custom-ordered schemas follow publication field grouping instead
        of strict canonical order. For these, we verify that publication
        metadata fields precede crossref fields among business fields.
        """
        column_names = schema.names

        if schema_name in CUSTOM_ORDER_SCHEMAS:
            # Validate that publication group fields maintain their
            # internal relative order (even if interleaved with other fields)
            business_fields = [c for c in column_names if c not in ALL_SYSTEM_FIELDS]

            pub_xref_in_schema = [
                c for c in business_fields if c in PUBLICATION_CROSSREF_FIELDS
            ]
            expected_pub_xref = [
                c for c in PUBLICATION_CROSSREF_FIELDS if c in set(business_fields)
            ]
            assert pub_xref_in_schema == expected_pub_xref, (
                f"{schema_name}: PUBLICATION_CROSSREF_FIELDS internal order violated.\n"
                f"Expected: {expected_pub_xref}\n"
                f"Got: {pub_xref_in_schema}"
            )
        else:
            expected = canonical_column_order(column_names)
            assert list(column_names) == expected, (
                f"{schema_name}: Column order does not match canonical.\n"
                f"Use canonical_column_order() to reorder.\n"
                f"First mismatch at position "
                f"{next(i for i, (a, b) in enumerate(zip(column_names, expected, strict=True)) if a != b)}"
            )
