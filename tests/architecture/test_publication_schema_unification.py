"""Tests for Publication Silver/Gold Schema Unification Strategy."""

import pandera.pandas as pa
import pytest

from bioetl.domain.contracts.gold.publication_base import PublicationGoldBaseSchema
from bioetl.domain.contracts.gold.publications import (
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
)

GOLD_SCHEMAS = [
    PubMedPublicationGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
]

NULLABLE_POLICY = {
    # Non-nullable in Gold (guaranteed by system)
    "entity_id": False,
    "content_hash": False,
    "run_id": False,
    "ingestion_ts": False,
    "index": False,
    "dq_warn": False,
    "dq_error": False,
    # Nullable (not all providers provide)
    "doi": True,
    "abstract": True,
    "authors": True,
    "citation_count": True,
    "doc_type": True,
}


class TestPublicationSchemaUnification:
    """Verify unified schema rules across providers."""

    def test_all_gold_schemas_inherit_base(self):
        """All Gold publication schemas must inherit PublicationGoldBaseSchema."""
        for schema in GOLD_SCHEMAS:
            assert issubclass(schema, PublicationGoldBaseSchema)

    def test_unified_fields_present_in_all(self):
        """Core unified fields must be present in all Gold schemas."""
        required_fields = {
            "entity_id",
            "content_hash",
            "title",
            "doi",
            "year",
            "citation_count",
            "_dq_warn",
            "_dq_error",
            "_run_id",
        }
        for schema in GOLD_SCHEMAS:
            schema_fields = set(schema.to_schema().columns.keys())
            missing = required_fields - schema_fields
            assert not missing, f"{schema.__name__} missing: {missing}"

    def test_year_range_unified(self):
        """Year field must have unified range 1450-2150."""
        for schema in GOLD_SCHEMAS:
            year_field = schema.to_schema().columns["year"]

            # Find the checks for ge and le
            ge_check = next(
                (c for c in year_field.checks if c.name == "greater_than_or_equal_to"),
                None,
            )
            le_check = next(
                (c for c in year_field.checks if c.name == "less_than_or_equal_to"),
                None,
            )

            assert ge_check is not None, f"{schema.__name__} year missing ge check"
            assert le_check is not None, f"{schema.__name__} year missing le check"

            # Check statistics
            assert (
                ge_check.statistics["min_value"] == 1450
            ), f"{schema.__name__} year ge != 1450"
            assert (
                le_check.statistics["max_value"] == 2150
            ), f"{schema.__name__} year le != 2150"

    def test_nullable_policy_consistent(self):
        """Nullable policy must match NULLABLE_POLICY spec."""
        for schema in GOLD_SCHEMAS:
            for field_name, expected_nullable in NULLABLE_POLICY.items():
                if field_name in schema.to_schema().columns:
                    # Special case: CrossRef uses DOI as PK (non-nullable)
                    if (
                        schema == CrossRefPublicationGoldSchema
                        and field_name == "doi"
                    ):
                        continue

                    actual = schema.to_schema().columns[field_name].nullable
                    assert (
                        actual == expected_nullable
                    ), f"{schema.__name__}.{field_name} nullable should be {expected_nullable}, got {actual}"
