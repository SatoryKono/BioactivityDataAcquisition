"""Unit tests for year validation across all publication schemas.

Tests unified year validation range (1950-CURRENT_YEAR+1) per RULES.md §2.3.2.
"""

from __future__ import annotations

import sys
from datetime import date
from uuid import uuid4

import pandas as pd
import pytest
from pandera.errors import SchemaError

from bioetl.domain.validation import MAX_PUBLICATION_YEAR, MIN_PUBLICATION_YEAR
from tests.helpers.clock import FIXED_TEST_TIME

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
        "_ingestion_ts": FIXED_TEST_TIME.isoformat(),
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
            "publication_year": 2020,
            "publication_date": "2020-06-15",  # Unified date field
            "publication_type": "journal-article",  # Raw CrossRef type (unified field name)
            "publication_type_unified": None,
            "publication_subclass": None,
            "publication_class": None,
            "language": "en",
            # Metrics (unified field names)
            "citations_received": 100,
            # Open Access
            "is_oa": None,
            # Lookup tracking
            "_lookup_method": "doi",
            "_original_id": "10.1038/nature12373",
            "_source": "crossref",
            # CrossRef-specific fields
            "issn": None,
            "issn_list": None,
            "publisher": "Nature Publishing Group",
            "volume": "1",
            "issue": "1",
            "page_first": "1",
            "page_last": "10",
            "published_print": None,
            "published_online": None,
            "citations_made": 50,
            "license_url": None,
            "subject_keywords": None,
            # Content domain fields
            "content_domain_domains": None,
            "content_domain_crossmark_restriction": None,
            # Additional CrossRef fields
            "alternative_id": None,
            "journal_name_short": None,
            "published": None,
            "issn_print": None,
            "issn_electronic": None,
            # Author affiliations
            "affiliation_list": None,
            # Author and reference fields
            "author_details": None,
            "references": None,
        }

    def test_year_boundary_values(self, valid_record: dict) -> None:
        """Should accept year at boundaries."""
        from bioetl.domain.schemas.crossref.publication import (
            PublicationEnrichedSchema,
        )

        for year in [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR]:
            valid_record["publication_year"] = year
            df = pd.DataFrame([valid_record])
            validated = PublicationEnrichedSchema.validate(df)
            assert validated["publication_year"].iloc[0] == year

    def test_year_outside_range_fails(self, valid_record: dict) -> None:
        """Should reject year outside valid range."""
        from bioetl.domain.schemas.crossref.publication import (
            PublicationEnrichedSchema,
        )

        # Year below minimum
        valid_record["publication_year"] = MIN_PUBLICATION_YEAR - 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            PublicationEnrichedSchema.validate(df)

        # Year above maximum
        valid_record["publication_year"] = MAX_PUBLICATION_YEAR + 1
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
            "publication_year": 2020,
            "publication_date": "2020-06-15",  # Unified date field
            "publication_type": "journal-article",
            "publication_type_unified": None,
            "publication_subclass": None,
            "publication_class": None,
            "language": None,
            # Metrics (unified field names)
            "citations_received": 100,
            # Open Access
            "is_oa": True,
            # Lookup tracking
            "_lookup_method": "doi",
            "_original_id": None,
            "_source": "semanticscholar",
            # SemanticScholar-specific fields
            "paper_id": "a" * 40,  # 40-char hex
            "dblp_id": None,
            "corpus_id": 12345,
            "tldr": None,
            "volume": None,
            "page_range": None,
            "page_first": None,
            "page_last": None,
            "citations_made": 50,
            "influential_citation_count": None,
            "open_access_url": None,
            "oa_status": None,
            "subject_fields": None,
            "subject_fields_canonical_json": None,
            "subject_fields_raw_json": None,
            "publication_types": None,
            "publication_types_canonical_json": None,
            "publication_types_raw_json": None,
            # Author affiliations
            "affiliation_list": None,
            # Author identifiers
            "author_s2_ids": None,
            "author_h_indices": None,
            "author_h_indices_canonical_json": None,
            "author_h_indices_raw_json": None,
            # Citation context
            "citation_contexts": None,
            "citation_contexts_canonical_json": None,
            "citation_contexts_raw_json": None,
        }

    def test_year_boundary_values(self, valid_record: dict) -> None:
        """Should accept year at boundaries."""
        from bioetl.domain.schemas.semanticscholar.publication import (
            SemanticScholarPublicationSchema,
        )

        for year in [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR]:
            valid_record["publication_year"] = year
            df = pd.DataFrame([valid_record])
            validated = SemanticScholarPublicationSchema.validate(df)
            assert validated["publication_year"].iloc[0] == year

    def test_year_outside_range_fails(self, valid_record: dict) -> None:
        """Should reject year outside valid range."""
        from bioetl.domain.schemas.semanticscholar.publication import (
            SemanticScholarPublicationSchema,
        )

        # Year below minimum
        valid_record["publication_year"] = MIN_PUBLICATION_YEAR - 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            SemanticScholarPublicationSchema.validate(df)

        # Year above maximum
        valid_record["publication_year"] = MAX_PUBLICATION_YEAR + 1
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
            "publication_year": 2020,
            "publication_date": None,  # Always NULL for ChEMBL
            "publication_type": "journal-article",
            "publication_type_unified": None,
            "publication_subclass": None,
            "publication_class": None,
            "language": None,
            # Affiliations (unified field name)
            "affiliation_list": None,
            # Metrics (unified field names, always NULL for ChEMBL)
            "citations_received": None,
            "citations_made": None,
            # Open Access (always NULL for ChEMBL)
            "is_oa": None,
            # Lookup tracking
            "_lookup_method": "direct",
            "_original_id": None,
            # System field (per SYSTEM_FIELDS_PREFIX)
            "_source": "chembl",
            # ChEMBL-specific fields
            "publication_id": "CHEMBL1234567",
            "src_id": 1,
            "volume": "1",
            "issue": "1",
            "page_first": "1",
            "page_last": "10",
            # ChEMBL release metadata
            "chembl_release": "CHEMBL_34",
            "creation_date": "2024-01-15",
        }

    def test_year_boundary_values(self, valid_record: dict) -> None:
        """Should accept year at boundaries."""
        from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema

        for year in [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR]:
            valid_record["publication_year"] = year
            df = pd.DataFrame([valid_record])
            validated = ChemblPublicationSchema.validate(df)
            assert validated["publication_year"].iloc[0] == year

    def test_year_outside_range_fails(self, valid_record: dict) -> None:
        """Should reject year outside valid range."""
        from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema

        # Year below minimum
        valid_record["publication_year"] = MIN_PUBLICATION_YEAR - 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            ChemblPublicationSchema.validate(df)

        # Year above maximum
        valid_record["publication_year"] = MAX_PUBLICATION_YEAR + 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            ChemblPublicationSchema.validate(df)


@PANDERA_PYTHON314_SKIP
class TestPubMedYearValidation:
    """Year validation tests for PubMedPublicationSchema.

    Note: PubMed uses 'year' field (renamed from 'pub_year').
    Canonical schema name follows ADR-024 publication naming.
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
            "journal": "Nature",  # Base schema journal field
            "journal_name_short": "Nature",  # PubMed-specific abbreviation (unified)
            "publication_year": 2020,
            "publication_date": "2020-05-15",  # Unified date field
            "publication_type": "journal-article",
            "publication_type_unified": None,
            "publication_subclass": None,
            "publication_class": None,
            "language": "eng",
            # Affiliations (unified field name)
            "affiliation_list": None,
            # Pagination (unified field names)
            "page_first": None,
            "page_last": None,
            # Metrics (unified field names)
            "citations_received": None,  # Not available from PubMed
            "citations_made": None,  # Unified name for reference count
            # Open Access
            "is_oa": None,
            # Lookup tracking
            "_lookup_method": "pmid",
            "_original_id": "12345678",
            "_source": "pubmed",
            # PubMed-specific fields
            "abstract_structured": None,
            "journal_iso_abbrev": "Nature",
            "issn": "0028-0836",
            "journal_issn_type": "Print",
            "nlm_unique_id": None,
            "country": "United States",
            "medline_pgn": "1-10",
            "page_range": "1-10",
            "pub_month": 5,
            "pub_day": 15,
            "publication_status": "ppublish",
            "publication_type_list": None,
            "date_completed": date(2020, 5, 20),
            "date_revised": date(2020, 5, 21),
            "citation_subset": None,
            # Enhanced affiliation data (unified field name)
            "affiliation_structured": None,
            "affiliation_structured_canonical_json": None,
            "affiliation_structured_raw_json": None,
            # Counts
            "author_count": 5,
            "mesh_heading_count": 10,
            "keyword_count": 3,
            "grant_count": 2,
            # reference_count removed — citations_made is the unified field
            "chemical_count": 0,
            # Classification data (JSON arrays, unified field names)
            "subject_mesh": None,
            "chemicals": None,
            "subject_keywords": None,
            "databanks": None,
            "gene_symbols": None,
            "publication_types": None,
            # Note: affiliation_list inherited from base (unified field name)
            # Author-affiliation mapping
            "authors_with_affiliations": None,
            "authors_with_affiliations_canonical_json": None,
            "authors_with_affiliations_raw_json": None,
        }

    def test_year_boundary_values(self, valid_record: dict) -> None:
        """Should accept year at boundaries."""
        from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema

        for year in [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR]:
            valid_record["publication_year"] = year
            df = pd.DataFrame([valid_record])
            validated = PubMedPublicationSchema.validate(df)
            assert validated["publication_year"].iloc[0] == year

    def test_year_outside_range_fails(self, valid_record: dict) -> None:
        """Should reject year outside valid range."""
        from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema

        # Year below minimum
        valid_record["publication_year"] = MIN_PUBLICATION_YEAR - 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            PubMedPublicationSchema.validate(df)

        # Year above maximum
        valid_record["publication_year"] = MAX_PUBLICATION_YEAR + 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            PubMedPublicationSchema.validate(df)

    def test_year_field_renamed_from_pub_year(self, valid_record: dict) -> None:
        """Verify 'publication_year' field is used instead of legacy 'pub_year'."""
        from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema

        # Record with 'publication_year' should work
        valid_record["publication_year"] = 2020
        df = pd.DataFrame([valid_record])
        validated = PubMedPublicationSchema.validate(df)
        assert "publication_year" in validated.columns

        # Verify there's no 'pub_year' column in schema
        assert "pub_year" not in validated.columns


class TestYearValidationConstants:
    """Test that all schemas use consistent year validation constants."""

    def test_constants_are_consistent(self) -> None:
        """Verify MIN and MAX publication year constants are correct."""
        assert MIN_PUBLICATION_YEAR == 1950
        assert MAX_PUBLICATION_YEAR == 2050

    def test_valid_year_range(self) -> None:
        """Test that constants define a valid range."""
        assert MIN_PUBLICATION_YEAR < MAX_PUBLICATION_YEAR
