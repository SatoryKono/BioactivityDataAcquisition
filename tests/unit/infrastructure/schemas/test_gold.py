"""Tests for Gold layer Pandera schemas.

Verifies schema definitions for various entities in the Gold layer,
with focus on publication schema unification.
"""

from __future__ import annotations

import pandas as pd
import pytest

# Import from contracts package (canonical location in domain layer)
from bioetl.domain.contracts import (
    ChEMBLDocumentGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
)


# Required fields for all publication schemas (unified across providers)
PUBLICATION_DQ_FIELDS = {"_dq_warn", "_dq_error"}
PUBLICATION_CROSS_REF_FIELDS = {"doi"}
PUBLICATION_UNIFIED_DATE_FIELDS = {"publication_date"}
PUBLICATION_UNIFIED_PAGE_FIELDS = {"first_page", "last_page"}
PUBLICATION_CORE_FIELDS = {"title", "abstract", "authors", "year"}


def get_schema_fields(schema_class) -> set[str]:
    """Extract field names from a Pandera DataFrameModel schema."""
    # Get all fields defined in the schema (including aliases)
    fields = set()
    for name, field in schema_class.__fields__.items():
        fields.add(name)
        # Also track the alias if it exists
        if hasattr(field, "alias") and field.alias:
            fields.add(field.alias)
    return fields


@pytest.mark.unit
class TestGoldPublicationSchemaDQFields:
    """Test that all Gold publication schemas have DQ fields."""

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_dq_fields(self, schema_class, name):
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
            # ChEMBL excluded: publication_date not available from ChEMBL API
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_publication_date(self, schema_class, name):
        """All Gold publication schemas must have publication_date field."""
        fields = get_schema_fields(schema_class)
        assert "publication_date" in fields, f"{name} missing publication_date field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            # OpenAlex doesn't have page fields - they were removed as unused
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_page_fields(self, schema_class, name):
        """Gold publication schemas with page data must have first_page and last_page fields."""
        fields = get_schema_fields(schema_class)
        assert "first_page" in fields, f"{name} missing first_page field"
        assert "last_page" in fields, f"{name} missing last_page field"


@pytest.mark.unit
class TestGoldPublicationSchemaCrossRefFields:
    """Test that all Gold publication schemas have cross-reference ID fields."""

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_doi_field(self, schema_class, name):
        """All Gold publication schemas must have doi field."""
        fields = get_schema_fields(schema_class)
        assert "doi" in fields, f"{name} missing doi field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            # CrossRef excluded: pmid explicitly excluded from transformer output
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_pmid_field(self, schema_class, name):
        """All Gold publication schemas should have pmid field."""
        fields = get_schema_fields(schema_class)
        assert "pmid" in fields, f"{name} missing pmid field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            # ChEMBL excluded: pmc_id not available from ChEMBL API
            # CrossRef excluded: pmc_id explicitly excluded from transformer output
            # OpenAlex excluded: pmc_id explicitly excluded from transformer output
            # SemanticScholar excluded: pmc_id explicitly excluded from transformer output
            (PubMedPublicationGoldSchema, "PubMed Publication"),
        ],
    )
    def test_schema_has_pmc_id_field(self, schema_class, name):
        """All Gold publication schemas should have pmc_id field."""
        fields = get_schema_fields(schema_class)
        assert "pmc_id" in fields, f"{name} missing pmc_id field"


@pytest.mark.unit
class TestGoldPublicationSchemaCoreFields:
    """Test that all Gold publication schemas have core content fields."""

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            # CrossRef excluded: abstract not collected per user request
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            # SemanticScholar excluded: abstract not collected per user request
        ],
    )
    def test_schema_has_title_and_abstract(self, schema_class, name):
        """All Gold publication schemas must have title and abstract fields."""
        fields = get_schema_fields(schema_class)
        assert "title" in fields, f"{name} missing title field"
        assert "abstract" in fields, f"{name} missing abstract field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            # SemanticScholar excluded: authors not collected per user request
        ],
    )
    def test_schema_has_authors_field(self, schema_class, name):
        """All Gold publication schemas must have authors field."""
        fields = get_schema_fields(schema_class)
        assert "authors" in fields, f"{name} missing authors field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_year_field(self, schema_class, name):
        """All Gold publication schemas must have year field."""
        fields = get_schema_fields(schema_class)
        assert "year" in fields, f"{name} missing year field"


@pytest.mark.unit
class TestGoldPublicationSchemaPrimaryKeys:
    """Test that each Gold publication schema has its provider-specific primary key."""

    @pytest.mark.parametrize(
        "schema_class,name,primary_key",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document", "document_chembl_id"),
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
    def test_schema_has_primary_key(self, schema_class, name, primary_key):
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
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_lookup_method_field(self, schema_class, name):
        """All Gold publication schemas must have _lookup_method field."""
        fields = get_schema_fields(schema_class)
        has_lookup_method = "_lookup_method" in fields or "lookup_method" in fields
        assert has_lookup_method, f"{name} missing _lookup_method/lookup_method field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_original_id_field(self, schema_class, name):
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
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_entity_id(self, schema_class, name):
        """All Gold schemas must have entity_id field."""
        fields = get_schema_fields(schema_class)
        assert "entity_id" in fields, f"{name} missing entity_id field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_content_hash(self, schema_class, name):
        """All Gold schemas must have content_hash field."""
        fields = get_schema_fields(schema_class)
        assert "content_hash" in fields, f"{name} missing content_hash field"

    @pytest.mark.parametrize(
        "schema_class,name",
        [
            (ChEMBLDocumentGoldSchema, "ChEMBL Document"),
            (CrossRefPublicationGoldSchema, "CrossRef Publication"),
            (OpenAlexPublicationGoldSchema, "OpenAlex Publication"),
            (PubMedPublicationGoldSchema, "PubMed Publication"),
            (SemanticScholarPublicationGoldSchema, "SemanticScholar Publication"),
        ],
    )
    def test_schema_has_lineage_fields(self, schema_class, name):
        """All Gold schemas must have lineage metadata fields."""
        fields = get_schema_fields(schema_class)
        # Check for alias or regular field names
        assert "_run_id" in fields or "run_id" in fields, (
            f"{name} missing run_id/_run_id field"
        )
        assert "_run_type" in fields or "run_type" in fields, (
            f"{name} missing run_type/_run_type field"
        )
        assert "_ingestion_ts" in fields or "ingestion_ts" in fields, (
            f"{name} missing ingestion_ts/_ingestion_ts field"
        )


@pytest.mark.unit
class TestGoldSchemaValidation:
    """Test Gold schema validation with sample data."""

    def test_pubmed_publication_validates_correct_data(self):
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
            "journal_abbrev": "Test J",
            "journal_title": "Test Journal Full Name",
            "journal_iso_abbrev": "Test J.",
            "journal_issn_type": "Print",
            "issn": "1234-5678",
            "nlm_unique_id": "7501160",
            "volume": "10",
            "issue": "2",
            "pages": "100-110",
            "medline_pgn": "100-110",
            "first_page": "100",
            "last_page": "110",
            "authors": '["Author One", "Author Two"]',
            # affiliations excluded per user request
            "pub_date": "2024-03-15",
            "pub_month": 3,
            "pub_day": 15,
            "publication_date": "2024-03-15",
            "year": 2024,
            "publication_year": 2024,
            # Note: accepted_date, received_date, revised_date, epub_date excluded per design
            "date_completed": "2024-04-01",
            "date_revised": "2024-03-20",
            "publication_status": "ppublish",
            "publication_type_list": '["Journal Article"]',
            "publication_types": ["Journal Article"],
            "keywords": ["test"],
            "mesh_terms": ["Testing"],
            "chemicals": ["Aspirin"],
            "databanks": ["GenBank"],
            "gene_symbols": ["TP53"],
            "citation_subset": "AIM",
            "language": "eng",
            "country": "United States",
            # Counts (denormalized for query efficiency)
            "author_count": 2,
            "mesh_heading_count": 1,
            "keyword_count": 1,
            "grant_count": 0,
            "reference_count": 10,
            "chemical_count": 0,
            "_source": "pubmed",
            "_lookup_method": "direct",
            "_original_id": "12345678",
            "_dq_warn": False,
            "_dq_error": False,
            "_run_id": "run-001",
            "_run_type": "incremental",
            "_source_batch_id": "batch-001",
            "_ingestion_ts": "2024-01-01T00:00:00Z",
            "_index": 0,
        }

        df = pd.DataFrame([valid_record])
        validated = PubMedPublicationGoldSchema.validate(df)

        assert len(validated) == 1
        assert validated["pmid"].iloc[0] == "12345678"

    def test_chembl_document_validates_correct_data(self):
        """ChEMBLDocumentGoldSchema should validate correct data."""
        valid_record = {
            "entity_id": "chembl_CHEMBL12345",
            "content_hash": "xyz789",
            "document_chembl_id": "CHEMBL12345",
            "pmid": "12345678",
            # pmc_id excluded: not available from ChEMBL API
            "doi": "10.1234/test",
            # patent_id excluded from unified publication schema
            "title": "Test Publication",
            "authors": '["Author One"]',
            "abstract": "Test abstract",
            "doc_type": "PUBLICATION",
            "journal": "Test Journal",
            "journal_full_title": "Test Journal Full Title",
            "year": 2024,
            # publication_date excluded: not available from ChEMBL API
            "volume": "10",
            "issue": "2",
            "first_page": "100",
            "last_page": "110",
            "src_id": 1,
            # ChEMBL release metadata
            "chembl_release": "CHEMBL_34",
            "creation_date": "2024-01-01",
            # Unified publication fields (ChEMBL doesn't provide these)
            "citation_count": None,
            "is_oa": False,  # Use False for nullable bool compatibility
            "language": None,
            "_lookup_method": "direct",
            "_original_id": "CHEMBL12345",
            "_source": "chembl",
            "_dq_warn": False,
            "_dq_error": False,
            "_run_id": "run-001",
            "_run_type": "incremental",
            "_source_batch_id": "batch-001",
            "_ingestion_ts": "2024-01-01T00:00:00Z",
            "_index": 0,
        }

        df = pd.DataFrame([valid_record])
        validated = ChEMBLDocumentGoldSchema.validate(df)

        assert len(validated) == 1
        assert validated["document_chembl_id"].iloc[0] == "CHEMBL12345"
