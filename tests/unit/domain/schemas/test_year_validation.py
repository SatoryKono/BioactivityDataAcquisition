"""Unit tests for year validation across all publication schemas.

Tests unified year validation range (1800-2100) per RULES.md §2.3.2.
"""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime
from uuid import uuid4

import pandas as pd
import pytest
from pandera.errors import SchemaError

from bioetl.domain.validation import MAX_PUBLICATION_YEAR, MIN_PUBLICATION_YEAR

# Pandera DataFrameModel has issues with Python 3.14+ due to function dispatch bug
PANDERA_PYTHON314_SKIP = pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason="Pandera DataFrameModel has compatibility issues with Python 3.14",
)


@pytest.fixture
def base_etl_fields() -> dict:
    """Create base ETL fields required by all schemas."""
    return {
        "entity_id": "test:entity:1",
        "content_hash": "a" * 64,
        "_run_id": uuid4(),
        "_run_type": "incremental",
        "_source_batch_id": None,
        "_ingestion_ts": datetime.now(UTC).isoformat(),
        "_dq_warn": False,
        "_dq_error": False,
        "_index": 0,
    }


@PANDERA_PYTHON314_SKIP
class TestCrossRefYearValidation:
    """Year validation tests for CrossRef PublicationEnrichedSchema."""

    @pytest.fixture
    def valid_record(self, base_etl_fields: dict) -> dict:
        """Create a valid CrossRef publication record."""
        return {
            **base_etl_fields,
            "entity_id": "crossref:publication:10.1038/nature12373",
            # Excluded from Silver/Gold schemas - CrossRef API doesn't provide PubMed identifiers
            "pmid": None,
            "doi": "10.1038/nature12373",
            "pmc_id": None,
            # Core content
            "title": "Test Publication",
            "abstract": None,
            "authors": '["Author A", "Author B"]',  # JSON array
            # Publication metadata
            "journal": "Nature",
            "year": 2020,
            "publication_date": "2020-06-15",  # Unified date field
            "doc_type": None,  # Excluded from Silver/Gold - CrossRef uses 'type' field
            "type": "journal-article",  # Raw CrossRef type (replaces doc_type)
            "language": "en",
            # Metrics
            "citation_count": 100,
            # Open Access
            "is_oa": None,
            # Lookup tracking
            "_lookup_method": "doi",
            "_original_id": "10.1038/nature12373",
            "_source": "crossref",
            # CrossRef-specific fields
            "issn": None,
            "publisher": "Nature Publishing Group",
            "volume": "1",
            "issue": "1",
            "first_page": "1",
            "last_page": "10",
            "published_print": None,
            "published_online": None,
            "reference_count": 50,
            "license_url": None,
            "subjects": None,
            # Content domain fields
            "content_domain_domains": None,
            "content_domain_crossmark_restriction": None,
            # Additional CrossRef fields
            "alternative_id": None,
            "short_container_title": None,
            "published": None,
            "issn_print": None,
            "issn_electronic": None,
            # Author affiliations
            "affiliations": None,
            # Author and reference fields
            "author_orcids": None,
            "author_details": None,
            "references": None,
        }

    def test_year_boundary_values(self, valid_record: dict) -> None:
        """Should accept year at boundaries (1800 and 2100)."""
        from bioetl.domain.schemas.crossref.publication import (
            PublicationEnrichedSchema,
        )

        for year in [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR]:
            valid_record["year"] = year
            df = pd.DataFrame([valid_record])
            validated = PublicationEnrichedSchema.validate(df)
            assert validated["year"].iloc[0] == year

    def test_year_outside_range_fails(self, valid_record: dict) -> None:
        """Should reject year outside valid range."""
        from bioetl.domain.schemas.crossref.publication import (
            PublicationEnrichedSchema,
        )

        # Year below minimum
        valid_record["year"] = MIN_PUBLICATION_YEAR - 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            PublicationEnrichedSchema.validate(df)

        # Year above maximum
        valid_record["year"] = MAX_PUBLICATION_YEAR + 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            PublicationEnrichedSchema.validate(df)


@PANDERA_PYTHON314_SKIP
class TestSemanticScholarYearValidation:
    """Year validation tests for SemanticScholarPublicationSchema."""

    @pytest.fixture
    def valid_record(self, base_etl_fields: dict) -> dict:
        """Create a valid Semantic Scholar publication record."""
        return {
            **base_etl_fields,
            "entity_id": "semanticscholar:publication:abc123",
            # Cross-reference IDs
            "pmid": None,
            "doi": "10.1038/nature12373",
            "pmc_id": None,
            # Core content
            "title": "Test Publication",
            "abstract": None,
            "authors": '["Author A", "Author B"]',  # JSON array
            # Publication metadata
            "journal": "Nature",
            "year": 2020,
            "publication_date": "2020-06-15",  # Unified date field
            "doc_type": "PUBLICATION",
            "language": None,
            # Metrics
            "citation_count": 100,
            # Open Access
            "is_oa": True,
            # Lookup tracking
            "_lookup_method": "doi",
            "_original_id": None,
            "_source": "semanticscholar",
            # SemanticScholar-specific fields
            "paper_id": "a" * 40,  # 40-char hex
            "arxiv_id": None,
            "dblp_id": None,
            "corpus_id": 12345,
            "tldr": None,
            "volume": None,
            "pages": None,
            "first_page": None,
            "last_page": None,
            "venue": None,
            "reference_count": 50,
            "influential_citation_count": None,
            "open_access_url": None,
            "oa_status": None,
            "fields_of_study": None,
            "publication_types": None,
            # Author affiliations
            "affiliations": None,
            # Author identifiers
            "author_s2_ids": None,
            "author_orcids": None,
            "author_h_indices": None,
            # Citation context
            "citation_contexts": None,
        }

    def test_year_boundary_values(self, valid_record: dict) -> None:
        """Should accept year at boundaries (1800 and 2100)."""
        from bioetl.domain.schemas.semanticscholar.publication import (
            SemanticScholarPublicationSchema,
        )

        for year in [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR]:
            valid_record["year"] = year
            df = pd.DataFrame([valid_record])
            validated = SemanticScholarPublicationSchema.validate(df)
            assert validated["year"].iloc[0] == year

    def test_year_outside_range_fails(self, valid_record: dict) -> None:
        """Should reject year outside valid range."""
        from bioetl.domain.schemas.semanticscholar.publication import (
            SemanticScholarPublicationSchema,
        )

        # Year below minimum (was 1500, now 1800)
        valid_record["year"] = MIN_PUBLICATION_YEAR - 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            SemanticScholarPublicationSchema.validate(df)

        # Year above maximum
        valid_record["year"] = MAX_PUBLICATION_YEAR + 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            SemanticScholarPublicationSchema.validate(df)


@PANDERA_PYTHON314_SKIP
class TestChemblYearValidation:
    """Year validation tests for ChemblPublicationSchema."""

    @pytest.fixture
    def valid_record(self, base_etl_fields: dict) -> dict:
        """Create a valid ChEMBL publication record."""
        return {
            **base_etl_fields,
            "entity_id": "chembl:publication:CHEMBL1234567",
            # Cross-reference IDs
            "pmid": "12345678",
            "doi": "10.1038/nature12373",
            "pmc_id": None,  # Always NULL for ChEMBL
            # Core content
            "title": "Test Publication",
            "abstract": "Abstract text",
            "authors": '["Author A", "Author B"]',  # JSON array
            # Publication metadata
            "journal": "Nature",
            "year": 2020,
            "publication_date": None,  # Always NULL for ChEMBL
            "doc_type": "PUBLICATION",
            "language": None,
            # Metrics (always NULL for ChEMBL)
            "citation_count": None,
            # Open Access (always NULL for ChEMBL)
            "is_oa": None,
            # Lookup tracking
            "_lookup_method": "direct",
            "_original_id": None,
            # System field (per SYSTEM_FIELDS_PREFIX)
            "_source": "chembl",
            # ChEMBL-specific fields
            "document_chembl_id": "CHEMBL1234567",
            "src_id": 1,
            "journal_full_title": "Nature Journal",
            "volume": "1",
            "issue": "1",
            "first_page": "1",
            "last_page": "10",
            # ChEMBL release metadata
            "chembl_release": "CHEMBL_34",
            "creation_date": "2024-01-15",
        }

    def test_year_boundary_values(self, valid_record: dict) -> None:
        """Should accept year at boundaries (1800 and 2100)."""
        from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema

        for year in [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR]:
            valid_record["year"] = year
            df = pd.DataFrame([valid_record])
            validated = ChemblPublicationSchema.validate(df)
            assert validated["year"].iloc[0] == year

    def test_year_outside_range_fails(self, valid_record: dict) -> None:
        """Should reject year outside valid range."""
        from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema

        # Year below minimum
        valid_record["year"] = MIN_PUBLICATION_YEAR - 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            ChemblPublicationSchema.validate(df)

        # Year above maximum
        valid_record["year"] = MAX_PUBLICATION_YEAR + 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            ChemblPublicationSchema.validate(df)


@PANDERA_PYTHON314_SKIP
class TestPubMedYearValidation:
    """Year validation tests for PubMedPublicationSchema.

    Note: PubMed uses 'year' field (renamed from 'pub_year').
    Schema renamed from ArticleSchema per ADR-024.
    """

    @pytest.fixture
    def valid_record(self, base_etl_fields: dict) -> dict:
        """Create a valid PubMed article record."""
        return {
            **base_etl_fields,
            "entity_id": "pubmed:article:12345678",
            # Cross-reference IDs (pmid is str for cross-provider consistency)
            "pmid": "12345678",
            "doi": "10.1038/nature12373",
            "pmc_id": None,
            # Additional identifiers
            "pii": None,
            "mid": None,
            "publisher_id": None,
            # Core content
            "title": "Test Article",
            "abstract": None,
            "authors": '["Author A", "Author B"]',  # JSON array
            # Publication metadata
            "journal": "Nature",  # Unified journal field
            "year": 2020,
            "publication_date": "2020-05-15",  # Unified date field
            "doc_type": "PUBLICATION",
            "language": "eng",
            # Metrics
            "citation_count": None,  # Not available from PubMed
            # Open Access
            "is_oa": None,
            # Lookup tracking
            "_lookup_method": "pmid",
            "_original_id": "12345678",
            "_source": "pubmed",
            # PubMed-specific fields
            "abstract_structured": None,
            "vernacular_title": None,
            "journal_title": "Nature",
            "journal_iso_abbrev": "Nature",
            "issn": "0028-0836",
            "journal_issn_type": "Print",
            "nlm_unique_id": None,
            "country": "United States",
            "medline_pgn": "1-10",
            "pub_month": 5,
            "pub_day": 15,
            "publication_status": "ppublish",
            "publication_type_list": None,
            "date_completed": date(2020, 5, 20),
            "date_revised": date(2020, 5, 21),
            "citation_subset": None,
            # Enhanced affiliation data
            "structured_affiliations": None,
            # Counts
            "author_count": 5,
            "mesh_heading_count": 10,
            "keyword_count": 3,
            "grant_count": 2,
            "reference_count": 50,
            "chemical_count": 0,
            # Classification data (JSON arrays)
            "mesh_terms": None,
            "chemicals": None,
            "keywords": None,
            "databanks": None,
            "gene_symbols": None,
            "publication_types": None,
            # Additional date fields
            "accepted_date": None,
            "received_date": None,
            "revised_date": None,
            "epub_date": None,
            # Author affiliations
            "affiliations": None,
            # Author-affiliation mapping
            "authors_with_affiliations": None,
        }

    def test_year_boundary_values(self, valid_record: dict) -> None:
        """Should accept year at boundaries (1800 and 2100)."""
        from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema

        for year in [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR]:
            valid_record["year"] = year
            df = pd.DataFrame([valid_record])
            validated = PubMedPublicationSchema.validate(df)
            assert validated["year"].iloc[0] == year

    def test_year_outside_range_fails(self, valid_record: dict) -> None:
        """Should reject year outside valid range."""
        from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema

        # Year below minimum
        valid_record["year"] = MIN_PUBLICATION_YEAR - 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            PubMedPublicationSchema.validate(df)

        # Year above maximum
        valid_record["year"] = MAX_PUBLICATION_YEAR + 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            PubMedPublicationSchema.validate(df)

    def test_year_field_renamed_from_pub_year(self, valid_record: dict) -> None:
        """Verify 'year' field is used instead of legacy 'pub_year'."""
        from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema

        # Record with 'year' should work
        valid_record["year"] = 2020
        df = pd.DataFrame([valid_record])
        validated = PubMedPublicationSchema.validate(df)
        assert "year" in validated.columns

        # Verify there's no 'pub_year' column in schema
        assert "pub_year" not in validated.columns


class TestYearValidationConstants:
    """Test that all schemas use consistent year validation constants."""

    def test_constants_are_consistent(self) -> None:
        """Verify MIN and MAX publication year constants are correct."""
        assert MIN_PUBLICATION_YEAR == 1800
        assert MAX_PUBLICATION_YEAR == 2100

    def test_valid_year_range(self) -> None:
        """Test that constants define a valid range."""
        assert MIN_PUBLICATION_YEAR < MAX_PUBLICATION_YEAR
        # Range should cover reasonable scientific publication history
        assert MAX_PUBLICATION_YEAR - MIN_PUBLICATION_YEAR == 300
