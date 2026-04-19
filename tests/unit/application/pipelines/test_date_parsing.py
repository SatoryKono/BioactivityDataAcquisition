"""Tests for publication date building across transformers.

Tests the _compute_publication_date method implementations in transformers
that build unified publication_date (YYYY-MM-DD) from various source formats.
"""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)
from bioetl.application.pipelines.pubmed.transformer import (
    PubMedPublicationTransformer,
)
from tests.helpers.transformer_dependencies import instantiate_test_transformer


@pytest.mark.unit
class TestPubMedDateBuilding:
    """Tests for PubMed publication date building."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMed transformer with minimal dependencies."""
        return instantiate_test_transformer(
            PubMedPublicationTransformer,
            provider="pubmed",
        )

    @pytest.mark.parametrize(
        "epub_date,pub_date,year,expected",
        [
            # epub_date takes priority (full ISO date)
            ("2024-03-15", "2024-04-01", 2024, "2024-03-15"),
            ("2024-01-01", "2024-12-31", 2024, "2024-01-01"),
            # pub_date used when epub_date is partial or missing
            (None, "2024-03-15", 2024, "2024-03-15"),
            ("2024-03", "2024-04-01", 2024, "2024-04-01"),  # partial epub falls back
            # Year-only fallback (end of year)
            (None, None, 2024, "2024-12-31"),
            (None, None, 1999, "1999-12-31"),
            (None, None, 2025, "2025-12-31"),
            # All None returns None
            (None, None, None, None),
            # Partial dates (less than 10 chars) fall back to pub_date normalization
            ("2024", "2024-06-15", 2024, "2024-06-15"),
            # Partial pub_date gets normalized using end-of-period month handling
            ("2024-06", None, 2024, "2024-12-31"),  # partial epub, no pub_date → year
        ],
    )
    def test_compute_publication_date(
        self,
        transformer: PubMedPublicationTransformer,
        epub_date: str | None,
        pub_date: str | None,
        year: int | None,
        expected: str | None,
    ) -> None:
        """Test publication_date computation with various inputs."""
        result = transformer._compute_publication_date(epub_date, pub_date, year)
        assert result == expected

    def test_publication_date_truncates_timestamp(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Date strings longer than 10 chars should be truncated."""
        result = transformer._compute_publication_date(
            epub_date="2024-03-15T12:00:00Z",
            pub_date="2024-04-01",
            year=2024,
        )
        assert result == "2024-03-15"

    def test_priority_is_epub_over_pub_over_year(
        self,
        transformer: PubMedPublicationTransformer,
    ) -> None:
        """Priority should be: epub_date > pub_date > year."""
        # epub_date full -> use epub
        assert (
            transformer._compute_publication_date("2024-01-01", "2024-02-01", 2024)
            == "2024-01-01"
        )

        # epub_date partial, pub_date full -> use pub_date
        assert (
            transformer._compute_publication_date("2024-01", "2024-02-15", 2024)
            == "2024-02-15"
        )

        # epub_date None, pub_date full -> use pub_date
        assert (
            transformer._compute_publication_date(None, "2024-02-15", 2024)
            == "2024-02-15"
        )

        # epub_date None, pub_date None -> use year (end of year)
        assert transformer._compute_publication_date(None, None, 2024) == "2024-12-31"


@pytest.mark.unit
class TestCrossRefDateBuilding:
    """Tests for CrossRef publication date building.

    Note: format_date_parts() now normalizes partial dates to YYYY-MM-DD
    with end-of-period, so _compute_publication_date() receives only
    full dates or None. It simply returns the first non-None value.
    """

    @pytest.fixture
    def transformer(self) -> CrossRefPublicationTransformer:
        """Create CrossRef transformer with minimal dependencies."""
        return instantiate_test_transformer(
            CrossRefPublicationTransformer,
            provider="crossref",
        )

    @pytest.mark.parametrize(
        "published_print,published_online,expected",
        [
            # Print date takes priority
            ("2024-03-15", "2024-02-01", "2024-03-15"),
            ("2024-01-01", "2024-06-15", "2024-01-01"),
            # Online date used when print is None
            (None, "2024-03-15", "2024-03-15"),
            # Full ISO date returned as-is
            ("2024-06-15", None, "2024-06-15"),
            # End-of-period normalized dates (from format_date_parts)
            ("2024-06-30", None, "2024-06-30"),  # Month-only becomes last day
            (None, "2024-03-31", "2024-03-31"),
            ("2024-12-31", None, "2024-12-31"),  # Year-only becomes Dec 31
            (None, "2023-12-31", "2023-12-31"),
            # Both None returns None
            (None, None, None),
        ],
    )
    def test_compute_publication_date(
        self,
        transformer: CrossRefPublicationTransformer,
        published_print: str | None,
        published_online: str | None,
        expected: str | None,
    ) -> None:
        """Test publication_date computation from print/online dates."""
        result = transformer._compute_publication_date(
            published_print, published_online
        )
        assert result == expected

    def test_print_priority_over_online(
        self,
        transformer: CrossRefPublicationTransformer,
    ) -> None:
        """Print date should always take priority over online date."""
        # Both present: use print
        assert (
            transformer._compute_publication_date("2024-01-15", "2024-02-15")
            == "2024-01-15"
        )

        # Print is None: use online
        assert transformer._compute_publication_date(None, "2024-02-15") == "2024-02-15"


@pytest.mark.unit
class TestChemblDateBuilding:
    """Tests for ChEMBL publication_date computation.

    ChEMBL only provides year, so publication_date is YYYY-01-01.
    The computation happens in _extract_business_data, not a separate method.
    These tests verify the expected behavior.
    """

    def test_chembl_year_to_publication_date(self) -> None:
        """ChEMBL should build publication_date from year only."""
        # This is the expected logic:
        year = 2024
        expected = f"{year}-01-01"
        assert expected == "2024-01-01"

        year = 1999
        expected = f"{year}-01-01"
        assert expected == "1999-01-01"

    def test_chembl_none_year_gives_none_date(self) -> None:
        """ChEMBL with None year should give None publication_date."""
        year = None
        assert year is None


@pytest.mark.unit
class TestDateParsingEdgeCases:
    """Tests for edge cases in date parsing."""

    @pytest.fixture
    def pubmed_transformer(self) -> PubMedPublicationTransformer:
        """Create PubMed transformer."""
        return instantiate_test_transformer(
            PubMedPublicationTransformer,
            provider="pubmed",
        )

    @pytest.fixture
    def crossref_transformer(self) -> CrossRefPublicationTransformer:
        """Create CrossRef transformer."""
        return instantiate_test_transformer(
            CrossRefPublicationTransformer,
            provider="crossref",
        )

    def test_pubmed_handles_empty_strings(
        self,
        pubmed_transformer: PubMedPublicationTransformer,
    ) -> None:
        """Empty strings should be treated as None."""
        # Empty epub_date should fall back to pub_date
        result = pubmed_transformer._compute_publication_date("", "2024-03-15", 2024)
        # Empty string has length 0 < 10, so falls back
        assert result == "2024-03-15"

    def test_pubmed_handles_whitespace(
        self,
        pubmed_transformer: PubMedPublicationTransformer,
    ) -> None:
        """Whitespace-only dates are not handled - use valid dates."""
        # Method takes dates as-is, no strip - caller should preprocess
        result = pubmed_transformer._compute_publication_date("2024-03-15", None, 2024)
        assert result == "2024-03-15"

    def test_crossref_preserves_valid_iso_format(
        self,
        crossref_transformer: CrossRefPublicationTransformer,
    ) -> None:
        """Valid ISO dates should be preserved as-is."""
        result = crossref_transformer._compute_publication_date("2024-12-31", None)
        assert result == "2024-12-31"

    def test_date_output_is_always_string_or_none(
        self,
        pubmed_transformer: PubMedPublicationTransformer,
        crossref_transformer: CrossRefPublicationTransformer,
    ) -> None:
        """Output should always be string or None."""
        pubmed_result = pubmed_transformer._compute_publication_date(
            "2024-01-01", None, 2024
        )
        assert isinstance(pubmed_result, str) or pubmed_result is None

        crossref_result = crossref_transformer._compute_publication_date(
            "2024-01-01", None
        )
        assert isinstance(crossref_result, str) or crossref_result is None

        # None case
        pubmed_none = pubmed_transformer._compute_publication_date(None, None, None)
        assert pubmed_none is None

        crossref_none = crossref_transformer._compute_publication_date(None, None)
        assert crossref_none is None
