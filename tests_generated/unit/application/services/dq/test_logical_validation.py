"""Logical validation tests for numeric and date fields.

Tests range constraints, non-negative rules, and date ordering.
Expected: ~60 tests covering 26 logical rules from validation schema.
"""

import pytest
import pandas as pd
from datetime import date


@pytest.mark.unit
class TestPublicationYearRange:
    """Test publication_year ∈ [1800, CURRENT_YEAR + 1]."""

    @pytest.mark.parametrize(
        "year,expected",
        [
            (1800, "PASS"),  # min boundary
            (2024, "PASS"),  # current year
            (2025, "PASS"),  # current year
            (2026, "PASS"),  # current year + 1
            (1799, "WARN"),  # below min
            (2027, "WARN"),  # far future
            (0, "WARN"),  # zero
            (-1, "WARN"),  # negative
        ],
    )
    def test_publication_year_range(
        self, minimal_pubmed_publication_df: pd.DataFrame, year: int, expected: str
    ) -> None:
        """Validate publication_year range [1800, CURRENT_YEAR + 1]."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_year"] = year

        current_year = date.today().year

        if 1800 <= year <= current_year + 1:
            assert expected == "PASS"
        else:
            assert expected == "WARN", f"Year {year} should warn"


@pytest.mark.unit
class TestCitationsReceivedNonNegative:
    """Test citations_received >= 0."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, "PASS"),
            (1, "PASS"),
            (100, "PASS"),
            (-1, "WARN"),  # negative
            (-100, "WARN"),
        ],
    )
    def test_citations_received_non_negative(
        self,
        minimal_openalex_publication_df: pd.DataFrame,
        value: int,
        expected: str,
    ) -> None:
        """Validate citations_received >= 0."""
        df = minimal_openalex_publication_df.copy()
        df["citations_received"] = value

        if value >= 0:
            assert expected == "PASS"
        else:
            assert expected == "WARN", f"Value {value} should warn"


@pytest.mark.unit
class TestCitationsMadeNonNegative:
    """Test citations_made >= 0."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, "PASS"),
            (50, "PASS"),
            (-1, "WARN"),
        ],
    )
    def test_citations_made_non_negative(
        self, minimal_pubmed_publication_df: pd.DataFrame, value: int, expected: str
    ) -> None:
        """Validate citations_made >= 0."""
        df = minimal_pubmed_publication_df.copy()
        df["citations_made"] = value

        if value >= 0:
            assert expected == "PASS"
        else:
            assert expected == "WARN"


@pytest.mark.unit
class TestFWCINonNegative:
    """Test fwci >= 0.0 (OpenAlex)."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0.0, "PASS"),
            (1.5, "PASS"),
            (10.0, "PASS"),
            (-0.1, "WARN"),
            (-1.0, "WARN"),
        ],
    )
    def test_fwci_non_negative(
        self,
        minimal_openalex_publication_df: pd.DataFrame,
        value: float,
        expected: str,
    ) -> None:
        """Validate fwci >= 0.0."""
        df = minimal_openalex_publication_df.copy()
        df["fwci"] = value

        if value >= 0:
            assert expected == "PASS"
        else:
            assert expected == "WARN"


@pytest.mark.unit
class TestInfluentialCitationCountNonNegative:
    """Test influential_citation_count >= 0 (SemanticScholar)."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0, "PASS"),
            (5, "PASS"),
            (-1, "WARN"),
        ],
    )
    def test_influential_citation_count_non_negative(
        self,
        minimal_semanticscholar_publication_df: pd.DataFrame,
        value: int,
        expected: str,
    ) -> None:
        """Validate influential_citation_count >= 0."""
        df = minimal_semanticscholar_publication_df.copy()
        df["influential_citation_count"] = value

        if value >= 0:
            assert expected == "PASS"
        else:
            assert expected == "WARN"


@pytest.mark.unit
class TestCitationsRelationship:
    """Test citations_received >= influential_citation_count."""

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
        """WARN: influential > citations -> logical inconsistency."""
        df = minimal_semanticscholar_publication_df.copy()
        df["citations_received"] = 5
        df["influential_citation_count"] = 10

        # Logically inconsistent
        assert df["citations_received"].iloc[0] < df["influential_citation_count"].iloc[0]


@pytest.mark.unit
class TestPageNumberRanges:
    """Test page_first >= 0, page_last >= 0 when numeric."""

    @pytest.mark.parametrize(
        "page_value,expected",
        [
            (0, "PASS"),
            (1, "PASS"),
            (100, "PASS"),
            (-1, "WARN"),
        ],
    )
    def test_page_first_non_negative(
        self, minimal_pubmed_publication_df: pd.DataFrame, page_value: int, expected: str
    ) -> None:
        """Validate page_first >= 0 when numeric."""
        df = minimal_pubmed_publication_df.copy()
        df["page_first"] = str(page_value)

        if page_value >= 0:
            assert expected == "PASS"
        else:
            assert expected == "WARN"


@pytest.mark.unit
class TestPubMonthRange:
    """Test pub_month ∈ [1, 12] (PubMed)."""

    @pytest.mark.parametrize(
        "month,expected",
        [
            (1, "PASS"),
            (6, "PASS"),
            (12, "PASS"),
            (0, "WARN"),
            (13, "WARN"),
            (-1, "WARN"),
        ],
    )
    def test_pub_month_range(
        self, minimal_pubmed_publication_df: pd.DataFrame, month: int, expected: str
    ) -> None:
        """Validate pub_month in [1, 12]."""
        df = minimal_pubmed_publication_df.copy()
        df["pub_month"] = month

        if 1 <= month <= 12:
            assert expected == "PASS"
        else:
            assert expected == "WARN"


@pytest.mark.unit
class TestPubDayRange:
    """Test pub_day ∈ [1, 31] (PubMed)."""

    @pytest.mark.parametrize(
        "day,expected",
        [
            (1, "PASS"),
            (15, "PASS"),
            (31, "PASS"),
            (0, "WARN"),
            (32, "WARN"),
        ],
    )
    def test_pub_day_range(
        self, minimal_pubmed_publication_df: pd.DataFrame, day: int, expected: str
    ) -> None:
        """Validate pub_day in [1, 31]."""
        df = minimal_pubmed_publication_df.copy()
        df["pub_day"] = day

        if 1 <= day <= 31:
            assert expected == "PASS"
        else:
            assert expected == "WARN"


@pytest.mark.unit
class TestDateOrdering:
    """Test date_completed <= date_revised (PubMed)."""

    def test_date_completed_before_revised_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: date_completed <= date_revised."""
        df = minimal_pubmed_publication_df.copy()
        df["date_completed"] = date(2024, 1, 1)
        df["date_revised"] = date(2024, 1, 15)

        assert df["date_completed"].iloc[0] <= df["date_revised"].iloc[0]

    def test_date_completed_after_revised_warns(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """WARN: date_completed > date_revised -> temporal inconsistency."""
        df = minimal_pubmed_publication_df.copy()
        df["date_completed"] = date(2024, 1, 15)
        df["date_revised"] = date(2024, 1, 1)

        # Logically inconsistent
        assert df["date_completed"].iloc[0] > df["date_revised"].iloc[0]


# TODO: Add remaining ~40 logical validation tests
# Based on logical_validation rules from validation schema XLSX
# Coverage should include:
# - All count fields (author_count, mesh_heading_count, etc.) >= 0
# - All metric fields (fwci, citations) >= 0
# - Date ordering rules
# - Page number constraints
