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
        "_ingestion_ts": datetime.now(UTC),
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
        from bioetl.domain.schemas.crossref.publication import DOCUMENT_TYPES

        return {
            **base_etl_fields,
            "entity_id": "crossref:publication:10.1038/nature12373",
            "doi": "10.1038/nature12373",
            "title": "Test Publication",
            "abstract": None,
            "authors": None,
            "journal": "Nature",
            "issn": None,
            "publisher": "Nature Publishing Group",
            "volume": "1",
            "issue": "1",
            "first_page": "1",
            "last_page": "10",
            "year": 2020,
            "published_print": None,
            "published_online": None,
            "doc_type": DOCUMENT_TYPES[0],
            "citation_count": 100,
            "reference_count": 50,
            "language": "en",
            "license_url": None,
            "subjects": None,
            "source": "crossref",
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
            "paper_id": "a" * 40,  # 40-char hex
            "doi": "10.1038/nature12373",
            "pmid": None,
            "pmcid": None,
            "arxiv_id": None,
            "corpus_id": 12345,
            "title": "Test Publication",
            "abstract": None,
            "tldr": None,
            "year": 2020,
            "publication_date": None,
            "journal": "Nature",
            "volume": None,
            "pages": None,
            "venue": None,
            "citation_count": 100,
            "reference_count": 50,
            "is_oa": True,
            "open_access_url": None,
            "oa_status": None,
            "fields_of_study": None,
            "publication_types": None,
            "authors": None,
            "source": "semanticscholar",
            "_lookup_method": "doi",
            "_original_doi": None,
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
            "document_chembl_id": "CHEMBL1234567",
            "pubmed_id": "12345678",
            "doi": "10.1038/nature12373",
            "patent_id": None,
            "src_id": 1,
            "title": "Test Publication",
            "doc_type": "PUBLICATION",
            "authors": "Author A, Author B",
            "abstract": "Abstract text",
            "journal": "Nature",
            "journal_full_title": "Nature Journal",
            "year": 2020,
            "volume": "1",
            "issue": "1",
            "first_page": "1",
            "last_page": "10",
        }

    def test_year_boundary_values(self, valid_record: dict) -> None:
        """Should accept year at boundaries (1800 and 2100)."""
        from bioetl.domain.schemas.chembl.document import ChemblPublicationSchema

        for year in [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR]:
            valid_record["year"] = year
            df = pd.DataFrame([valid_record])
            validated = ChemblPublicationSchema.validate(df)
            assert validated["year"].iloc[0] == year

    def test_year_outside_range_fails(self, valid_record: dict) -> None:
        """Should reject year outside valid range."""
        from bioetl.domain.schemas.chembl.document import ChemblPublicationSchema

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
    """Year validation tests for ArticleSchema (PubMed).

    Note: PubMed uses 'year' field (renamed from 'pub_year').
    """

    @pytest.fixture
    def valid_record(self, base_etl_fields: dict) -> dict:
        """Create a valid PubMed article record."""
        return {
            **base_etl_fields,
            "entity_id": "pubmed:article:12345678",
            "pmid": 12345678,
            "doi": "10.1038/nature12373",
            "pmc_id": None,
            "title": "Test Article",
            "abstract": None,
            "abstract_structured": None,
            "vernacular_title": None,
            "language": "eng",
            "journal_title": "Nature",
            "journal_iso_abbrev": "Nature",
            "journal_issn": "0028-0836",
            "journal_issn_type": "Print",
            "nlm_unique_id": None,
            "country": "United States",
            "volume": "1",
            "issue": "1",
            "medline_pgn": "1-10",
            "year": 2020,
            "pub_month": 5,
            "pub_day": 15,
            "publication_status": "ppublish",
            "publication_type_list": None,
            "date_completed": date(2020, 5, 20),
            "date_revised": date(2020, 5, 21),
            "citation_subset": None,
            "author_count": 5,
            "mesh_heading_count": 10,
            "keyword_count": 3,
            "grant_count": 2,
            "reference_count": 50,
            "chemical_count": 0,
        }

    def test_year_boundary_values(self, valid_record: dict) -> None:
        """Should accept year at boundaries (1800 and 2100)."""
        from bioetl.domain.schemas.pubmed.article import ArticleSchema

        for year in [MIN_PUBLICATION_YEAR, MAX_PUBLICATION_YEAR]:
            valid_record["year"] = year
            df = pd.DataFrame([valid_record])
            validated = ArticleSchema.validate(df)
            assert validated["year"].iloc[0] == year

    def test_year_outside_range_fails(self, valid_record: dict) -> None:
        """Should reject year outside valid range."""
        from bioetl.domain.schemas.pubmed.article import ArticleSchema

        # Year below minimum
        valid_record["year"] = MIN_PUBLICATION_YEAR - 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            ArticleSchema.validate(df)

        # Year above maximum
        valid_record["year"] = MAX_PUBLICATION_YEAR + 1
        df = pd.DataFrame([valid_record])
        with pytest.raises(SchemaError):
            ArticleSchema.validate(df)

    def test_year_field_renamed_from_pub_year(self, valid_record: dict) -> None:
        """Verify 'year' field is used instead of legacy 'pub_year'."""
        from bioetl.domain.schemas.pubmed.article import ArticleSchema

        # Record with 'year' should work
        valid_record["year"] = 2020
        df = pd.DataFrame([valid_record])
        validated = ArticleSchema.validate(df)
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
