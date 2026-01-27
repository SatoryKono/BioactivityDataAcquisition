"""Architecture test: Publication Schema Unification.

Verifies that all publication Gold schemas follow unified rules:
- All inherit from PublicationGoldBaseSchema
- Unified fields are present in all schemas
- Year range is unified (1450-2150)
- Nullable policy is consistent
- DQ and lineage fields are inherited correctly
"""

from __future__ import annotations

import pytest

from bioetl.domain.contracts.gold.publication_base import PublicationGoldBaseSchema
from bioetl.domain.contracts.gold.publications import (
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
)

# All publication Gold schemas
PUBLICATION_GOLD_SCHEMAS = [
    PubMedPublicationGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
]

# Fields that MUST be present in all publication Gold schemas (inherited from base)
REQUIRED_UNIFIED_FIELDS = {
    "entity_id",
    "content_hash",
    "doi",
    "pmid",
    "pmc_id",
    "title",
    "authors",
    "journal",
    "volume",
    "first_page",
    "last_page",
    "year",
    "publication_date",
    "doc_type",
    "language",
    "citation_count",
    "reference_count",
}

# Lineage fields that MUST be present in all schemas
REQUIRED_LINEAGE_FIELDS = {
    "_source",
    "_lookup_method",
    "_original_id",
    "_dq_warn",
    "_dq_error",
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_ingestion_ts",
    "_index",
}

# Non-nullable fields in base schema
NON_NULLABLE_BASE_FIELDS = {
    "entity_id",
    "content_hash",
    "_dq_warn",
    "_dq_error",
    "_run_id",
    "_run_type",
    "_ingestion_ts",
    "_index",
}

# Nullable fields in base schema (can be overridden to non-nullable in subclasses)
NULLABLE_BASE_FIELDS = {
    "doi",
    "pmid",
    "pmc_id",
    "title",
    "authors",
    "journal",
    "volume",
    "first_page",
    "last_page",
    "year",
    "publication_date",
    "doc_type",
    "language",
    "citation_count",
    "reference_count",
    "_source",
    "_lookup_method",
    "_original_id",
    "_source_batch_id",
}


class TestPublicationSchemaInheritance:
    """Tests verifying all publication schemas inherit from base."""

    @pytest.mark.parametrize(
        "schema",
        PUBLICATION_GOLD_SCHEMAS,
        ids=lambda s: s.__name__,
    )
    def test_schema_inherits_from_base(self, schema: type) -> None:
        """All publication Gold schemas MUST inherit from PublicationGoldBaseSchema."""
        assert issubclass(schema, PublicationGoldBaseSchema), (
            f"{schema.__name__} must inherit from PublicationGoldBaseSchema. "
            "This ensures cross-provider query compatibility and unified field definitions."
        )

    def test_base_schema_is_not_a_provider_schema(self) -> None:
        """PublicationGoldBaseSchema should not be used directly as a provider schema."""
        assert PublicationGoldBaseSchema not in PUBLICATION_GOLD_SCHEMAS, (
            "PublicationGoldBaseSchema is a base class and should not be used "
            "directly as a provider schema."
        )


class TestUnifiedFieldsPresent:
    """Tests verifying unified fields are present in all schemas."""

    @pytest.mark.parametrize(
        "schema",
        PUBLICATION_GOLD_SCHEMAS,
        ids=lambda s: s.__name__,
    )
    def test_required_unified_fields_present(self, schema: type) -> None:
        """All publication schemas MUST have required unified fields."""
        # Get schema fields from Pandera model
        pandera_schema = schema.to_schema()
        schema_columns = set(pandera_schema.columns.keys())

        missing = REQUIRED_UNIFIED_FIELDS - schema_columns
        assert not missing, (
            f"{schema.__name__} missing unified fields:\n"
            + "\n".join(f"  - {f}" for f in sorted(missing))
            + "\n\nThese fields are required for cross-provider query compatibility."
        )

    @pytest.mark.parametrize(
        "schema",
        PUBLICATION_GOLD_SCHEMAS,
        ids=lambda s: s.__name__,
    )
    def test_lineage_fields_present(self, schema: type) -> None:
        """All publication schemas MUST have lineage fields."""
        pandera_schema = schema.to_schema()
        schema_columns = set(pandera_schema.columns.keys())

        missing = REQUIRED_LINEAGE_FIELDS - schema_columns
        assert not missing, (
            f"{schema.__name__} missing lineage fields:\n"
            + "\n".join(f"  - {f}" for f in sorted(missing))
            + "\n\nLineage fields are required per RULES.md Section 2.4."
        )


class TestUnifiedConstraints:
    """Tests verifying unified constraints across all schemas."""

    @pytest.mark.parametrize(
        "schema",
        PUBLICATION_GOLD_SCHEMAS,
        ids=lambda s: s.__name__,
    )
    def test_year_range_unified(self, schema: type) -> None:
        """Year field MUST have unified range 1450-2150 in all schemas."""
        pandera_schema = schema.to_schema()
        year_column = pandera_schema.columns.get("year")

        assert year_column is not None, f"{schema.__name__} missing 'year' field"

        # Extract ge/le checks from column using Pandera's statistics attribute
        checks = year_column.checks
        ge_value = None
        le_value = None

        for check in checks:
            if hasattr(check, "statistics"):
                stats = check.statistics
                if "min_value" in stats:
                    ge_value = stats["min_value"]
                if "max_value" in stats:
                    le_value = stats["max_value"]

        # The base schema defines year with ge=1450, le=2150
        # Provider schemas inherit this constraint
        assert ge_value == 1450, (
            f"{schema.__name__}.year has incorrect lower bound: {ge_value}. "
            f"Expected: 1450 (unified range per PublicationGoldBaseSchema)."
        )
        assert le_value == 2150, (
            f"{schema.__name__}.year has incorrect upper bound: {le_value}. "
            f"Expected: 2150 (unified range per PublicationGoldBaseSchema)."
        )

    @pytest.mark.parametrize(
        "schema",
        PUBLICATION_GOLD_SCHEMAS,
        ids=lambda s: s.__name__,
    )
    def test_doc_type_is_nullable(self, schema: type) -> None:
        """doc_type field MUST be nullable in all schemas (unified policy)."""
        pandera_schema = schema.to_schema()
        doc_type_column = pandera_schema.columns.get("doc_type")

        assert doc_type_column is not None, f"{schema.__name__} missing 'doc_type' field"
        assert doc_type_column.nullable is True, (
            f"{schema.__name__}.doc_type must be nullable=True. "
            "Unified policy: not all providers supply doc_type."
        )

    @pytest.mark.parametrize(
        "schema",
        PUBLICATION_GOLD_SCHEMAS,
        ids=lambda s: s.__name__,
    )
    def test_citation_count_non_negative(self, schema: type) -> None:
        """citation_count field MUST have ge=0 constraint."""
        pandera_schema = schema.to_schema()
        citation_column = pandera_schema.columns.get("citation_count")

        assert citation_column is not None, f"{schema.__name__} missing 'citation_count'"

        # Check for ge=0 constraint using Pandera's statistics attribute
        has_ge_zero = False
        for check in citation_column.checks:
            if hasattr(check, "statistics"):
                stats = check.statistics
                if stats.get("min_value") == 0:
                    has_ge_zero = True
                    break

        assert has_ge_zero, (
            f"{schema.__name__}.citation_count must have ge=0 constraint. "
            "Citation counts cannot be negative."
        )


class TestNullablePolicy:
    """Tests verifying nullable policy is consistent."""

    @pytest.mark.parametrize(
        "schema",
        PUBLICATION_GOLD_SCHEMAS,
        ids=lambda s: s.__name__,
    )
    def test_non_nullable_fields_consistent(self, schema: type) -> None:
        """System fields MUST be non-nullable in all schemas."""
        pandera_schema = schema.to_schema()

        for field_name in NON_NULLABLE_BASE_FIELDS:
            column = pandera_schema.columns.get(field_name)
            if column is not None:
                assert column.nullable is False, (
                    f"{schema.__name__}.{field_name} must be non-nullable. "
                    "System fields are guaranteed by the pipeline."
                )


class TestPrimaryKeyPolicy:
    """Tests verifying primary key policy for each provider."""

    def test_pubmed_pmid_non_nullable(self) -> None:
        """PubMed schema MUST have pmid as non-nullable primary key."""
        pandera_schema = PubMedPublicationGoldSchema.to_schema()
        pmid_column = pandera_schema.columns.get("pmid")

        assert pmid_column is not None, "PubMedPublicationGoldSchema missing 'pmid'"
        assert pmid_column.nullable is False, (
            "PubMedPublicationGoldSchema.pmid must be non-nullable. "
            "pmid is the primary key for PubMed publications."
        )

    def test_crossref_doi_non_nullable(self) -> None:
        """CrossRef schema MUST have doi as non-nullable primary key."""
        pandera_schema = CrossRefPublicationGoldSchema.to_schema()
        doi_column = pandera_schema.columns.get("doi")

        assert doi_column is not None, "CrossRefPublicationGoldSchema missing 'doi'"
        assert doi_column.nullable is False, (
            "CrossRefPublicationGoldSchema.doi must be non-nullable. "
            "doi is the primary key for CrossRef publications."
        )

    def test_openalex_id_non_nullable(self) -> None:
        """OpenAlex schema MUST have openalex_id as non-nullable primary key."""
        pandera_schema = OpenAlexPublicationGoldSchema.to_schema()
        openalex_column = pandera_schema.columns.get("openalex_id")

        assert openalex_column is not None, "OpenAlexPublicationGoldSchema missing 'openalex_id'"
        assert openalex_column.nullable is False, (
            "OpenAlexPublicationGoldSchema.openalex_id must be non-nullable. "
            "openalex_id is the primary key for OpenAlex publications."
        )

    def test_s2_paper_id_non_nullable(self) -> None:
        """Semantic Scholar schema MUST have paper_id as non-nullable primary key."""
        pandera_schema = SemanticScholarPublicationGoldSchema.to_schema()
        paper_id_column = pandera_schema.columns.get("paper_id")

        assert paper_id_column is not None, "SemanticScholarPublicationGoldSchema missing 'paper_id'"
        assert paper_id_column.nullable is False, (
            "SemanticScholarPublicationGoldSchema.paper_id must be non-nullable. "
            "paper_id is the primary key for Semantic Scholar publications."
        )


class TestBaseSchemaConfig:
    """Tests verifying base schema configuration."""

    def test_base_schema_config_allows_subclass_fields(self) -> None:
        """Base schema Config.strict should allow subclasses to add fields."""
        config = PublicationGoldBaseSchema.Config
        # The base schema should use strict="filter" to allow subclasses to add fields
        assert hasattr(config, "strict"), "Base schema Config must have 'strict' attribute"
        assert config.strict == "filter", (
            "PublicationGoldBaseSchema.Config.strict should be 'filter' "
            "to allow provider-specific fields in subclasses."
        )

    @pytest.mark.parametrize(
        "schema",
        PUBLICATION_GOLD_SCHEMAS,
        ids=lambda s: s.__name__,
    )
    def test_provider_schemas_are_strict(self, schema: type) -> None:
        """Provider schemas should use strict=True for validation."""
        config = schema.Config
        assert hasattr(config, "strict"), f"{schema.__name__}.Config must have 'strict'"
        assert config.strict is True, (
            f"{schema.__name__}.Config.strict should be True "
            "to prevent unexpected columns in validated data."
        )


class TestAbstractFieldInclusion:
    """Tests verifying abstract field inclusion per unified policy."""

    def test_pubmed_has_abstract(self) -> None:
        """PubMed schema should include abstract field."""
        pandera_schema = PubMedPublicationGoldSchema.to_schema()
        assert "abstract" in pandera_schema.columns, (
            "PubMedPublicationGoldSchema should include 'abstract' field."
        )

    def test_openalex_has_abstract(self) -> None:
        """OpenAlex schema should include abstract field."""
        pandera_schema = OpenAlexPublicationGoldSchema.to_schema()
        assert "abstract" in pandera_schema.columns, (
            "OpenAlexPublicationGoldSchema should include 'abstract' field."
        )

    def test_semanticscholar_has_abstract(self) -> None:
        """Semantic Scholar schema should include abstract field (unified policy)."""
        pandera_schema = SemanticScholarPublicationGoldSchema.to_schema()
        assert "abstract" in pandera_schema.columns, (
            "SemanticScholarPublicationGoldSchema should include 'abstract' field. "
            "Per unified schema policy, abstract is now included for all providers."
        )
