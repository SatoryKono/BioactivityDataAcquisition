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
"""Tests for Gold layer Pandera schemas.

Verifies schema definitions for various entities in the Gold layer,
with focus on publication schema unification.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

# Import from contracts package (canonical location in domain layer)
from bioetl.domain.contracts import (
    ChEMBLPublicationGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
)


# Required fields for all publication schemas (unified across providers)
PUBLICATION_DQ_FIELDS = {"_dq_warn", "_dq_error"}
PUBLICATION_CROSS_REF_FIELDS = {"doi"}
PUBLICATION_UNIFIED_DATE_FIELDS = {"publication_date"}
PUBLICATION_UNIFIED_PAGE_FIELDS = {"page_first", "page_last"}
PUBLICATION_CORE_FIELDS = {"title", "abstract", "authors", "publication_year"}

SchemaType = type[Any]


def get_schema_fields(schema_class: SchemaType) -> set[str]:
    """Extract field names from a Pandera DataFrameModel schema."""
    # Pandera DataFrameModel does not have __fields__.
    # Use to_schema().columns to get the actual column names (including aliases).
    schema = schema_class.to_schema()
    return set(schema.columns.keys())


@pytest.mark.unit
class TestGoldPublicationSchemaDQFields:
    """Test that all Gold publication schemas have DQ fields."""

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_dq_fields(self, schema_class: SchemaType, name: str) -> None:
        """All Gold publication schemas must have DQ fields."""
        fields = get_schema_fields(schema_class)
        # Check for alias versions (_dq_warn, _dq_error) or regular versions
        has_dq_warn = "_dq_warn" in fields or "dq_warn" in fields
        has_dq_error = "_dq_error" in fields or "dq_error" in fields
        assert has_dq_warn, f"{name} missing _dq_warn/_dq_error field"
        assert has_dq_error, f"{name} missing _dq_error/dq_error field"


@pytest.mark.unit
class TestGoldPublicationSchemaUnifiedFields:
    """Test that all Gold publication schemas have unified date and page fields."""

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_publication_date(
        self, schema_class: SchemaType, name: str
    ) -> None:
        """Gold publication schemas with exact-date support must expose publication_date."""
        fields = get_schema_fields(schema_class)
        assert "publication_date" in fields, f"{name} missing publication_date field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            # OpenAlex doesn't have page fields - they were removed as unused
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_page_fields(self, schema_class: SchemaType, name: str) -> None:
        """Gold publication schemas with page data must have page_first and page_last fields."""
        fields = get_schema_fields(schema_class)
        assert "page_first" in fields, f"{name} missing page_first field"
        assert "page_last" in fields, f"{name} missing page_last field"


@pytest.mark.unit
class TestGoldPublicationSchemaCrossRefFields:
    """Test that all Gold publication schemas have cross-reference ID fields."""

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_doi_field(self, schema_class: SchemaType, name: str) -> None:
        """All Gold publication schemas must have doi field."""
        fields = get_schema_fields(schema_class)
        assert "doi" in fields, f"{name} missing doi field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            # CrossRef excluded: pmid explicitly excluded from transformer output
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_pmid_field(self, schema_class: SchemaType, name: str) -> None:
        """All Gold publication schemas should have pmid field."""
        fields = get_schema_fields(schema_class)
        assert "pmid" in fields, f"{name} missing pmid field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_pmc_id_field(self, schema_class: SchemaType, name: str) -> None:
        """Gold publication schemas with raw PMC IDs should expose pmc_id."""
        fields = get_schema_fields(schema_class)
        assert "pmc_id" in fields, f"{name} missing pmc_id field"


@pytest.mark.unit
class TestGoldPublicationSchemaCoreFields:
    """Test that all Gold publication schemas have core content fields."""

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            # CrossRef excluded: abstract not collected per user request
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_title_and_abstract(
        self, schema_class: SchemaType, name: str
    ) -> None:
        """All Gold publication schemas must have title and abstract fields."""
        fields = get_schema_fields(schema_class)
        assert "title" in fields, f"{name} missing title field"
        assert "abstract" in fields, f"{name} missing abstract field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            # SemanticScholar excluded: transformer pops raw authors,
            # uses author_s2_ids/author_orcids instead
        ],
    )
    def test_schema_has_authors_field(
        self, schema_class: SchemaType, name: str
    ) -> None:
        """Gold publication schemas with raw authors must have authors field."""
        fields = get_schema_fields(schema_class)
        assert "authors" in fields, f"{name} missing authors field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_publication_year_field(
        self, schema_class: SchemaType, name: str
    ) -> None:
        """All Gold publication schemas must have publication_year field."""
        fields = get_schema_fields(schema_class)
        assert "publication_year" in fields, f"{name} missing publication_year field"

    def test_chembl_schema_has_publication_year_field(self) -> None:
        """ChEMBL Gold schema uses publication_year (unified naming)."""
        fields = get_schema_fields(ChEMBLPublicationGoldSchema)
        assert "publication_year" in fields, (
            "ChEMBL Document missing publication_year field"
        )


@pytest.mark.unit
class TestGoldPublicationSchemaPrimaryKeys:
    """Test that each Gold publication schema has its provider-specific primary key."""

    @pytest.mark.parametrize(
        "schema_class,name,primary_key",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document", "publication_id"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication", "doi"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication", "openalex_id"),
            (PubMedPublicationGoldSchema, "PubMed Publication", "pmid"),
            (
                SemanticScholarPublicationGoldSchema,
                "SemanticScholar Publication",
                "paper_id",
            ),
        ],
    )
    def test_schema_has_primary_key(
        self, schema_class: SchemaType, name: str, primary_key: str
    ) -> None:
        """Each Gold publication schema must have its provider-specific primary key."""
        fields = get_schema_fields(schema_class)
        assert primary_key in fields, f"{name} missing primary key: {primary_key}"


@pytest.mark.unit
class TestGoldPublicationSchemaLookupTrackingFields:
    """Test that all Gold publication schemas have lookup tracking fields.

    These fields track how records were resolved during data acquisition:
    - _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    - _original_id: Original identifier used for lookup
    """

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_lookup_method_field(
        self, schema_class: SchemaType, name: str
    ) -> None:
        """All Gold publication schemas must have _lookup_method field."""
        fields = get_schema_fields(schema_class)
        has_lookup_method = "_lookup_method" in fields or "lookup_method" in fields
        assert has_lookup_method, f"{name} missing _lookup_method/lookup_method field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_original_id_field(
        self, schema_class: SchemaType, name: str
    ) -> None:
        """All Gold publication schemas must have _original_id field."""
        fields = get_schema_fields(schema_class)
        has_original_id = "_original_id" in fields or "original_id" in fields
        assert has_original_id, f"{name} missing _original_id/original_id field"


@pytest.mark.unit
class TestGoldPublicationSchemaMetadataFields:
    """Test that all Gold publication schemas have required metadata fields."""

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_entity_id(self, schema_class: SchemaType, name: str) -> None:
        """All Gold schemas must have entity_id field."""
        fields = get_schema_fields(schema_class)
        assert "entity_id" in fields, f"{name} missing entity_id field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_content_hash(self, schema_class: SchemaType, name: str) -> None:
        """All Gold schemas must have content_hash field."""
        fields = get_schema_fields(schema_class)
        assert "content_hash" in fields, f"{name} missing content_hash field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLPublicationGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_excludes_occurrence_lineage_fields(
        self, schema_class: SchemaType, name: str
    ) -> None:
        """Gold persisted-row contracts must exclude occurrence-scoped lineage fields."""
        fields = get_schema_fields(schema_class)
        assert "_run_id" not in fields and "run_id" not in fields, (
            f"{name} should not expose run_id in persisted Gold contract"
        )
        assert "_run_type" not in fields and "run_type" not in fields, (
            f"{name} should not expose run_type in persisted Gold contract"
        )
        assert "_source_batch_id" not in fields and "source_batch_id" not in fields, (
            f"{name} should not expose source_batch_id in persisted Gold contract"
        )
        assert "_ingestion_ts" not in fields and "ingestion_ts" not in fields, (
            f"{name} should not expose ingestion_ts in persisted Gold contract"
        )


@pytest.mark.unit
class TestGoldSchemaValidation:
    """Test Gold schema validation with sample data."""

    def test_pubmed_publication_validates_correct_data(self) -> None:
        """PubMedPublicationGoldSchema should validate correct data."""
        valid_record = {
            "entity_id": "pubmed_12345678",
            "content_hash": "abc123",
            "pmid": "12345678",
            "doi": "10.1234/test",
            "pmc_id": "PMC1234567",
            "title": "Test Title",
            "abstract": "Test abstract",
            # PubMed-specific fields for forensic retention
            "abstract_structured": False,
            # Note: vernacular_title excluded per design
            "journal": "Test Journal",
            "journal_name_short": "Test J",
            "journal_iso_abbrev": "Test J.",
            "journal_issn_type": "Print",
            "issn": "1234-5678",
            "issn_list": '["1234-5678"]',
            "nlm_unique_id": "7501160",
            "volume": "10",
            "issue": "2",
            "page_range": "100-110",
            "medline_pgn": "100-110",
            "page_first": "100",
            "page_last": "110",
            "authors": '["Author One", "Author Two"]',
            "author_keys": "One_A|Two_A",
            "affiliation_list": '["University A", "University B"]',
            "affiliation_structured": '[{"text": "University A", "ror_id": null}]',
            "affiliation_structured_raw_json": '[{"text": "University A", "ror_id": null}]',
            "affiliation_structured_canonical_json": '[{"text": "University A", "ror_id": null}]',
            "authors_with_affiliations": '[{"name_hash": "abc123", "initials": "AO", "affiliations": []}]',
            "authors_with_affiliations_raw_json": '[{"name_hash": "abc123", "initials": "AO", "affiliations": []}]',
            "authors_with_affiliations_canonical_json": (
                '[{"name_hash": "abc123", "initials": "AO", "affiliations": []}]'
            ),
            "pii": "S0123-4567(24)00001-X",
            "mid": "NIHMS123456",
            "publisher_id": "pub-12345",
            "pub_date": "2024 Mar 15",
            "pub_month": 3,
            "pub_day": 15,
            "publication_date": "2024-03-15",
            "publication_year": 2024,
            # Note: accepted_date, received_date, revised_date, epub_date excluded per design
            "date_completed": "2024-04-01",
            "date_revised": "2024-03-20",
            "publication_status": "ppublish",
            "publication_type": "journal-article",
            "publication_type_unified": "Journal Article",
            "publication_subclass": "Original Experimental Data",
            "publication_class": "EXP",
            "publication_types": '["Journal Article"]',
            "subject_keywords": '["test"]',
            "subject_mesh": '["Testing"]',
            "chemicals": '["Aspirin"]',
            "databanks": '["GenBank"]',
            "gene_symbols": '["TP53"]',
            "citation_subset": "AIM",
            "language": "eng",
            "country": "United States",
            # Counts (denormalized for query efficiency)
            "author_count": 2,
            "mesh_heading_count": 1,
            "keyword_count": 1,
            "grant_count": 0,
            "citations_made": 10,
            "chemical_count": 0,
            "_source": "pubmed",
            "_lookup_method": "direct",
            "_original_id": "12345678",
            "_dq_warn": False,
            "_dq_error": False,
            "_index": 0,
        }

        df = pd.DataFrame([valid_record])
        validated = PubMedPublicationGoldSchema.validate(df)

        assert len(validated) == 1
        assert validated["pmid"].iloc[0] == "12345678"

    def test_chembl_document_validates_correct_data(self) -> None:
        """ChEMBLPublicationGoldSchema should validate correct data."""
        valid_record = {
            "entity_id": "chembl_CHEMBL12345",
            "content_hash": "xyz789",
            "publication_id": "CHEMBL12345",
            # Cross-reference IDs (prefixed naming convention)
            "publication_doi": "10.1234/test",
            "publication_pmid": "12345678",
            "publication_pmc_id": None,
            # Cross-reference IDs (raw identifiers from Silver)
            "doi": "10.1234/test",
            "pmid": "12345678",
            "title": "Test Publication",
            "authors": '["Author One"]',
            "abstract": "Test abstract",
            "author_keys": None,
            "publication_type": "journal-article",
            "journal": "Test Journal",
            "publication_year": 2024,
            "volume": "10",
            "issue": "2",
            "page_first": "100",
            "page_last": "110",
            "citations_received": None,
            "citations_made": None,
            "src_id": 1,
            # ChEMBL release metadata
            "chembl_release": "CHEMBL_34",
            "creation_date": "2024-01-01",
            "_lookup_method": "direct",
            "_original_id": "CHEMBL12345",
            "_source": "chembl",
            "_dq_warn": False,
            "_dq_error": False,
            "_index": 0,
        }

        df = pd.DataFrame([valid_record])
        validated = ChEMBLPublicationGoldSchema.validate(df)

        assert len(validated) == 1
        assert validated["publication_id"].iloc[0] == "CHEMBL12345"
