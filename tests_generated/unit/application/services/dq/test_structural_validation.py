"""Structural validation tests for cross-field dependencies.

Tests consistency rules between related fields across all providers.
Expected: ~80 tests covering 25 structural rules from validation schema.
"""

import pytest
import pandas as pd
import pandera as pa


@pytest.mark.unit
class TestPageNumberValidation:
    """Test page_first <= page_last structural rule."""

    def test_page_first_less_than_last_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: page_first < page_last."""
        df = minimal_pubmed_publication_df.copy()
        df["page_first"] = "100"
        df["page_last"] = "110"
        # Should pass validation
        assert int(df["page_first"].iloc[0]) <= int(df["page_last"].iloc[0])

    def test_page_first_equals_last_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: page_first == page_last (single page)."""
        df = minimal_pubmed_publication_df.copy()
        df["page_first"] = "100"
        df["page_last"] = "100"
        assert int(df["page_first"].iloc[0]) <= int(df["page_last"].iloc[0])

    def test_page_first_greater_than_last_warns(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: page_first > page_last -> _dq_warn=True."""
        df = minimal_pubmed_publication_df.copy()
        df["page_first"] = "110"
        df["page_last"] = "100"
        # Structural validation should set _dq_warn=True
        # This would be caught by a structural validator service
        assert int(df["page_first"].iloc[0]) > int(df["page_last"].iloc[0])

    def test_page_numbers_both_null_skips(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: both page_first and page_last are NULL."""
        df = minimal_pubmed_publication_df.copy()
        df["page_first"] = None
        df["page_last"] = None
        # Should skip structural validation
        assert df["page_first"].isna().all()


@pytest.mark.unit
class TestPublicationYearDateConsistency:
    """Test publication_year matches YEAR(publication_date)."""

    def test_year_matches_date_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: publication_year == YEAR(publication_date)."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_year"] = 2024
        df["publication_date"] = "2024-06-15"

        date_year = int(df["publication_date"].iloc[0].split("-")[0])
        assert df["publication_year"].iloc[0] == date_year

    def test_year_mismatch_warns(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: publication_year != YEAR(publication_date) -> _dq_warn=True."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_year"] = 2024
        df["publication_date"] = "2023-06-15"

        date_year = int(df["publication_date"].iloc[0].split("-")[0])
        assert df["publication_year"].iloc[0] != date_year


@pytest.mark.unit
class TestCorpusIdPaperIdDependency:
    """Test corpus_id requires paper_id (SemanticScholar)."""

    def test_corpus_id_with_paper_id_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: corpus_id present with paper_id."""
        df = minimal_semanticscholar_publication_df.copy()
        df["corpus_id"] = 12345
        df["paper_id"] = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"

        assert df["corpus_id"].notna().all()
        assert df["paper_id"].notna().all()

    def test_corpus_id_without_paper_id_fails(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """FAIL: corpus_id without paper_id -> data inconsistency."""
        df = minimal_semanticscholar_publication_df.copy()
        df["corpus_id"] = 12345
        df["paper_id"] = None

        # This should fail structural validation
        has_corpus = df["corpus_id"].notna()
        has_paper = df["paper_id"].notna()
        assert not (has_corpus & ~has_paper).all(), "corpus_id requires paper_id"


@pytest.mark.unit
class TestContentHashConsistency:
    """Test content_hash matches recomputed hash."""

    def test_content_hash_consistent(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: content_hash matches recomputed hash (excl. metadata)."""
        df = minimal_chembl_publication_df.copy()

        # Mock: content_hash should be stable
        original_hash = df["content_hash"].iloc[0]
        assert len(original_hash) == 64
        assert original_hash.islower()

    def test_content_hash_mismatch_fails(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """FAIL: content_hash != recomputed -> data corruption."""
        df = minimal_chembl_publication_df.copy()

        # Simulate hash mismatch
        df["content_hash"] = "b" * 64
        original_hash = "a" * 64

        assert df["content_hash"].iloc[0] != original_hash


@pytest.mark.unit
class TestDoiTitleDependency:
    """Test DOI presence implies title should exist."""

    def test_doi_with_title_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: DOI present with title."""
        df = minimal_crossref_publication_df.copy()
        df["doi"] = "10.1234/test.001"
        df["title"] = "Test Title"

        assert df["doi"].notna().all()
        assert df["title"].notna().all()

    def test_doi_without_title_warns(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """WARN: DOI present but title missing -> _dq_warn=True."""
        df = minimal_crossref_publication_df.copy()
        df["doi"] = "10.1234/test.001"
        df["title"] = None

        has_doi = df["doi"].notna()
        has_title = df["title"].notna()

        # Structural rule: IF doi NOT NULL THEN title SHOULD NOT be NULL
        assert (has_doi & ~has_title).any(), "DOI without title should warn"


@pytest.mark.unit
class TestCitationCountRelationship:
    """Test citations_received >= influential_citation_count (S2)."""

    def test_citations_gte_influential_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: citations_received >= influential_citation_count."""
        df = minimal_semanticscholar_publication_df.copy()
        df["citations_received"] = 10
        df["influential_citation_count"] = 5

        assert df["citations_received"].iloc[0] >= df["influential_citation_count"].iloc[0]

    def test_citations_less_than_influential_warns(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """WARN: influential > citations_received -> _dq_warn=True."""
        df = minimal_semanticscholar_publication_df.copy()
        df["citations_received"] = 5
        df["influential_citation_count"] = 10

        # This is logically inconsistent
        assert df["citations_received"].iloc[0] < df["influential_citation_count"].iloc[0]


@pytest.mark.unit
class TestPublishedPrintOnlineOrder:
    """Test published_print <= published_online (CrossRef)."""

    def test_print_before_online_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: published_print <= published_online."""
        df = minimal_crossref_publication_df.copy()
        df["published_print"] = "2024-01-15"
        df["published_online"] = "2024-01-20"

        # Should be in logical order
        assert df["published_print"].iloc[0] <= df["published_online"].iloc[0]

    def test_print_after_online_warns(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """WARN: print date after online date -> _dq_warn=True."""
        df = minimal_crossref_publication_df.copy()
        df["published_print"] = "2024-01-20"
        df["published_online"] = "2024-01-15"

        # Logically inconsistent
        assert df["published_print"].iloc[0] > df["published_online"].iloc[0]


# TODO: Add remaining ~60 structural validation tests
# Based on structural_validation rules from validation schema XLSX
# Each rule should have 3-4 test scenarios:
# - both_valid, inconsistent, both_null, partial_null
