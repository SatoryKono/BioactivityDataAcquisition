"""Tests for page parsing utilities across transformers.

Tests the _parse_pages method implementations in PubMed and SemanticScholar
transformers that parse medline_pgn and pages strings into first_page/last_page.
"""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.pubmed.transformer import (
    PubMedPublicationTransformer,
)
from bioetl.application.pipelines.semanticscholar.transformer import (
    SemanticScholarPublicationTransformer,
)


@pytest.mark.unit
class TestPubMedMedlinePgnParsing:
    """Tests for PubMed medline_pgn parsing."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMed transformer with minimal dependencies."""
        return PubMedPublicationTransformer(provider="pubmed")

    @pytest.mark.parametrize(
        "pgn,expected_first,expected_last",
        [
            # Standard hyphenated range
            ("100-110", "100", "110"),
            ("1-999", "1", "999"),
            ("123-456", "123", "456"),
            # Single page number
            ("100", "100", None),
            ("1", "1", None),
            ("999999", "999999", None),
            # Electronic article numbers
            ("e100-e110", "e100", "e110"),
            ("E123-E456", "E123", "E456"),
            # Supplement pages
            ("S1-S10", "S1", "S10"),
            ("s100-s200", "s100", "s200"),
            # Short form (abbreviated last page)
            ("100-10", "100", "10"),
            ("1234-56", "1234", "56"),
            # Empty and None
            ("", None, None),
            (None, None, None),
            # Whitespace handling
            ("  100 - 110  ", "100", "110"),
            ("100 -110", "100", "110"),
            ("  100  ", "100", None),
            # Mixed formats
            ("A1-A10", "A1", "A10"),
            ("ii-x", "ii", "x"),
        ],
    )
    def test_parse_medline_pgn(
        self,
        transformer: PubMedPublicationTransformer,
        pgn: str | None,
        expected_first: str | None,
        expected_last: str | None,
    ) -> None:
        """Test various medline_pgn formats."""
        first, last = transformer._parse_pages(pgn)

        assert first == expected_first, f"First page mismatch for '{pgn}'"
        assert last == expected_last, f"Last page mismatch for '{pgn}'"

    def test_hyphen_only_returns_empty(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Single hyphen should return None for last page."""
        first, last = transformer._parse_pages("-")

        assert first is None
        assert last is None

    def test_parse_pages_immutability(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Parsing should not modify the original string."""
        original = "100-110"
        _ = transformer._parse_pages(original)

        assert original == "100-110"


@pytest.mark.unit
class TestSemanticScholarPagesParsing:
    """Tests for Semantic Scholar pages parsing."""

    @pytest.fixture
    def transformer(self) -> SemanticScholarPublicationTransformer:
        """Create SemanticScholar transformer with minimal dependencies."""
        return SemanticScholarPublicationTransformer(provider="semanticscholar")

    @pytest.mark.parametrize(
        "pages,expected_first,expected_last",
        [
            # Standard hyphenated range
            ("123-456", "123", "456"),
            ("1-10", "1", "10"),
            # Single page
            ("123", "123", None),
            ("1", "1", None),
            # Electronic articles
            ("e123-e456", "e123", "e456"),
            # Empty and None
            (None, None, None),
            ("", None, None),
            # Whitespace
            ("  100 - 200  ", "100", "200"),
            # Single page with whitespace
            ("  100  ", "100", None),
        ],
    )
    def test_parse_pages(
        self,
        transformer: SemanticScholarPublicationTransformer,
        pages: str | None,
        expected_first: str | None,
        expected_last: str | None,
    ) -> None:
        """Test various pages formats from Semantic Scholar."""
        first, last = transformer._parse_pages(pages)

        assert first == expected_first, f"First page mismatch for '{pages}'"
        assert last == expected_last, f"Last page mismatch for '{pages}'"


@pytest.mark.unit
class TestPageParsingConsistency:
    """Tests for consistency between transformer implementations."""

    @pytest.fixture
    def pubmed_transformer(self) -> PubMedPublicationTransformer:
        """Create PubMed transformer."""
        return PubMedPublicationTransformer(provider="pubmed")

    @pytest.fixture
    def s2_transformer(self) -> SemanticScholarPublicationTransformer:
        """Create SemanticScholar transformer."""
        return SemanticScholarPublicationTransformer(provider="semanticscholar")

    @pytest.mark.parametrize(
        "pages",
        [
            "100-200",
            "123",
            "e100-e200",
            None,
            "",
            "  100 - 200  ",
        ],
    )
    def test_parsing_consistency_across_transformers(
        self,
        pubmed_transformer: PubMedPublicationTransformer,
        s2_transformer: SemanticScholarPublicationTransformer,
        pages: str | None,
    ) -> None:
        """Both transformers should parse common formats consistently."""
        pubmed_first, pubmed_last = pubmed_transformer._parse_pages(pages)
        s2_first, s2_last = s2_transformer._parse_pages(pages)

        assert pubmed_first == s2_first, f"First page inconsistent for '{pages}'"
        assert pubmed_last == s2_last, f"Last page inconsistent for '{pages}'"


@pytest.mark.unit
class TestPmcIdNormalization:
    """Tests for PMC ID normalization in transformers."""

    @pytest.fixture
    def pubmed_transformer(self) -> PubMedPublicationTransformer:
        """Create PubMed transformer."""
        return PubMedPublicationTransformer(provider="pubmed")

    @pytest.fixture
    def s2_transformer(self) -> SemanticScholarPublicationTransformer:
        """Create SemanticScholar transformer."""
        return SemanticScholarPublicationTransformer(provider="semanticscholar")

    @pytest.mark.parametrize(
        "raw_pmc_id,expected",
        [
            # Already normalized
            ("PMC1234567", "PMC1234567"),
            # Lowercase PMC prefix
            ("pmc1234567", "PMC1234567"),
            # Missing prefix - should add PMC
            ("1234567", "PMC1234567"),
            # Mixed case
            ("Pmc1234567", "PMC1234567"),
            # None and empty
            (None, None),
            ("", None),
            # Whitespace
            ("  PMC1234567  ", "PMC1234567"),
            ("  1234567  ", "PMC1234567"),
        ],
    )
    def test_pubmed_pmc_id_normalization(
        self,
        pubmed_transformer: PubMedPublicationTransformer,
        raw_pmc_id: str | None,
        expected: str | None,
    ) -> None:
        """PubMed transformer should normalize PMC IDs correctly."""
        result = pubmed_transformer._normalize_pmc_id(raw_pmc_id)
        assert result == expected

    @pytest.mark.parametrize(
        "raw_pmc_id,expected",
        [
            ("PMC1234567", "PMC1234567"),
            ("pmc1234567", "PMC1234567"),
            ("1234567", "PMC1234567"),
            (None, None),
            ("", None),
        ],
    )
    def test_s2_pmc_id_normalization(
        self,
        s2_transformer: SemanticScholarPublicationTransformer,
        raw_pmc_id: str | None,
        expected: str | None,
    ) -> None:
        """SemanticScholar transformer should normalize PMC IDs correctly."""
        result = s2_transformer._normalize_pmc_id(raw_pmc_id)
        assert result == expected
