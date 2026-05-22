"""Integration tests for CrossRef date normalization.

Tests that publication date fields are correctly normalized to YYYY-MM-DD format
when transforming from Bronze to Silver layer.

CrossRef provides dates in various formats (end-of-period normalization):
- Full: [[2024, 3, 15]] -> "2024-03-15"
- Partial month: [[2024, 3]] -> "2024-03-31" (last day of month)
- Partial year: [[2024]] -> "2024-12-31" (last day of year)

Date fields tested:
- publication_date: Unified computed date (YYYY-MM-DD)
- published_print: Print publication date
- published_online: Online publication date
"""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

import pytest

from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import instantiate_test_transformer
from tests.integration.pipelines.observability import build_test_logger


# YYYY-MM-DD pattern
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Date fields that must follow YYYY-MM-DD format when present
CROSSREF_DATE_FIELDS = [
    "publication_date",
    "published_print",
    "published_online",
]


@pytest.fixture
def transformer() -> CrossRefPublicationTransformer:
    """Create CrossRef transformer with minimal dependencies."""
    return instantiate_test_transformer(
        CrossRefPublicationTransformer,
        provider="crossref",
    )


@pytest.fixture
def pipeline_context() -> PipelineContext:
    """Create a minimal pipeline context for transformation."""
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=build_test_logger(),
    )


def make_crossref_record(
    doi: str = "10.1234/test.123",
    title: str = "Test Publication",
    published_print: list[list[int]] | None = None,
    published_online: list[list[int]] | None = None,
) -> dict[str, Any]:
    """Generate CrossRef record for testing date extraction.

    Args:
        doi: DOI identifier
        title: Publication title
        published_print: Print date as [[YYYY, MM, DD]], [[YYYY, MM]], or [[YYYY]]
        published_online: Online date as [[YYYY, MM, DD]], [[YYYY, MM]], or [[YYYY]]

    Returns:
        CrossRef API-style record
    """
    record: dict[str, Any] = {
        "DOI": doi,
        "title": [title],
        "type": "journal-article",
    }

    if published_print is not None:
        record["published-print"] = {"date-parts": published_print}

    if published_online is not None:
        record["published-online"] = {"date-parts": published_online}

    return record


@pytest.mark.integration
class TestCrossRefDateNormalization:
    """Integration tests for CrossRef date normalization."""

    @pytest.mark.asyncio
    async def test_publication_date_format(
        self,
        transformer: CrossRefPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Publication_date field must be YYYY-MM-DD format."""
        record = make_crossref_record(published_print=[[2024, 3, 15]])

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        assert pub_date is not None, "publication_date should not be None"
        assert DATE_PATTERN.match(pub_date), (
            f"Invalid date format: {pub_date}, expected YYYY-MM-DD"
        )

    @pytest.mark.asyncio
    async def test_all_date_fields_format(
        self,
        transformer: CrossRefPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """All date fields must be YYYY-MM-DD format or None."""
        record = make_crossref_record(
            published_print=[[2024, 3, 15]],
            published_online=[[2024, 2, 28]],
        )

        result = await transformer.transform(pipeline_context, record, 0)

        for field in CROSSREF_DATE_FIELDS:
            value = result.get(field)
            if value is not None:
                assert DATE_PATTERN.match(value), (
                    f"Invalid {field} format: {value}, expected YYYY-MM-DD"
                )

    @pytest.mark.asyncio
    async def test_partial_date_year_only_normalization(
        self,
        transformer: CrossRefPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Year-only dates ([[2024]]) should be normalized to YYYY-12-31 (end of year)."""
        record = make_crossref_record(published_print=[[2024]])

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        assert pub_date == "2024-12-31", (
            f"Year-only date should normalize to YYYY-12-31, got {pub_date}"
        )

    @pytest.mark.asyncio
    async def test_partial_date_year_month_normalization(
        self,
        transformer: CrossRefPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Year-month dates ([[2024, 3]]) should be normalized to YYYY-MM-31 (last day)."""
        record = make_crossref_record(published_print=[[2024, 3]])

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        assert pub_date == "2024-03-31", (
            f"Year-month date should normalize to last day of month, got {pub_date}"
        )

    @pytest.mark.asyncio
    async def test_print_date_takes_priority_over_online(
        self,
        transformer: CrossRefPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Print date should take priority over online date."""
        record = make_crossref_record(
            published_print=[[2024, 6, 15]],
            published_online=[[2024, 3, 1]],
        )

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        assert pub_date == "2024-06-15", (
            f"Expected print date (2024-06-15) to take priority, got {pub_date}"
        )

    @pytest.mark.asyncio
    async def test_online_date_used_when_no_print(
        self,
        transformer: CrossRefPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Online date should be used when print date is missing."""
        record = make_crossref_record(published_online=[[2024, 3, 1]])

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        assert pub_date == "2024-03-01", (
            f"Expected online date when no print, got {pub_date}"
        )

    @pytest.mark.asyncio
    async def test_no_dates_returns_none(
        self,
        transformer: CrossRefPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """No dates should return None for publication_date."""
        record = make_crossref_record()

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        assert pub_date is None, f"Expected None when no dates, got {pub_date}"


@pytest.mark.unit
class TestCrossRefDateEdgeCases:
    """Edge case tests for CrossRef date handling.

    Note: _compute_publication_date is a passthrough selector that chooses
    between print and online dates. It does NOT normalize dates - normalization
    happens upstream in format_date_parts(). These tests verify the selection
    logic, not normalization.
    """

    @pytest.fixture
    def transformer(self) -> CrossRefPublicationTransformer:
        """Create CrossRef transformer."""
        return instantiate_test_transformer(
            CrossRefPublicationTransformer,
            provider="crossref",
        )

    @pytest.mark.parametrize(
        "published_print,published_online,expected",
        [
            # Full print date - prefers print
            ("2024-03-15", "2024-02-01", "2024-03-15"),
            # Already-normalized partial dates (from format_date_parts)
            ("2024-03-31", None, "2024-03-31"),
            ("2024-12-31", None, "2024-12-31"),
            # Print is None, use online
            (None, "2024-03-15", "2024-03-15"),
            # Both dates (print takes priority)
            ("2024-06-30", "2024-03-31", "2024-06-30"),
            # Both None
            (None, None, None),
        ],
    )
    def test_date_selection_combinations(
        self,
        transformer: CrossRefPublicationTransformer,
        published_print: str | None,
        published_online: str | None,
        expected: str | None,
    ) -> None:
        """Test date selection with already-normalized input dates.

        Note: _compute_publication_date receives dates that are already
        normalized by format_date_parts() in the extractors. It simply
        selects print over online, not performing additional normalization.
        """
        result = transformer._compute_publication_date(
            published_print, published_online
        )
        assert result == expected, (
            f"Expected {expected}, got {result} for print={published_print}, "
            f"online={published_online}"
        )

    @pytest.mark.parametrize(
        "date_str,expected",
        [
            # Full ISO date - passes through unchanged
            ("2024-12-31", "2024-12-31"),
            ("2024-03-15", "2024-03-15"),
            # _compute_publication_date is a pass-through selector
            ("2024-06-30", "2024-06-30"),
        ],
    )
    def test_date_passthrough(
        self,
        transformer: CrossRefPublicationTransformer,
        date_str: str,
        expected: str,
    ) -> None:
        """Test that _compute_publication_date passes dates through unchanged.

        Normalization is done by format_date_parts() in extractors, not here.
        """
        result = transformer._compute_publication_date(date_str, None)
        assert result == expected


@pytest.mark.integration
class TestCrossRefVCRIntegration:
    """Tests using VCR cassettes with real API response patterns.

    These tests verify that partial dates from real CrossRef API responses
    are correctly normalized to YYYY-MM-DD format.
    """

    @pytest.fixture
    def transformer(self) -> CrossRefPublicationTransformer:
        """Create CrossRef transformer."""
        return instantiate_test_transformer(
            CrossRefPublicationTransformer,
            provider="crossref",
        )

    @pytest.fixture
    def pipeline_context(self) -> PipelineContext:
        """Create pipeline context."""
        return PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=build_test_logger(),
        )

    @pytest.mark.asyncio
    async def test_real_api_partial_date_patterns(
        self,
        transformer: CrossRefPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test partial dates as they appear in real CrossRef API responses.

        CrossRef API returns dates in "date-parts" format:
        - [[2024, 3, 15]] for full date
        - [[2024, 3]] for year-month only -> "2024-03-31" (end of month)
        - [[2024]] for year only -> "2024-12-31" (end of year)
        """
        # Simulate a record with partial date [[2024, 3]] as returned by API
        record: dict[str, Any] = {
            "DOI": "10.1038/s41586-024-07000-0",
            "title": ["Nature Article with Partial Date"],
            "type": "journal-article",
            "published-print": {"date-parts": [[2024, 3]]},  # Partial: year-month only
        }

        result = await transformer.transform(pipeline_context, record, 0)

        # Should be normalized to end-of-month (2024-03-31)
        pub_date = result.get("publication_date")
        assert pub_date is not None
        assert DATE_PATTERN.match(pub_date), f"Invalid format: {pub_date}"
        assert pub_date == "2024-03-31"

    @pytest.mark.asyncio
    async def test_preprint_year_only_date(
        self,
        transformer: CrossRefPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test preprints that often have year-only dates.

        Year-only dates are normalized to end-of-year (YYYY-12-31).
        """
        record: dict[str, Any] = {
            "DOI": "10.1101/2024.01.01.123456",
            "title": ["Preprint with Year Only"],
            "type": "posted-content",
            "published-online": {"date-parts": [[2024]]},  # Year only
        }

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        assert pub_date == "2024-12-31"
