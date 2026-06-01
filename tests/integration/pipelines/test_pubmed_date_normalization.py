"""Integration tests for PubMed date normalization.

Tests that publication date fields are correctly normalized to YYYY-MM-DD format
when transforming from Bronze to Silver layer.

Date fields tested:
- publication_date: Unified computed date (YYYY-MM-DD)
- pub_date: Original publication date
- epub_date: Electronic publication date
- accepted_date: Manuscript acceptance date
- received_date: Manuscript received date
- revised_date: Manuscript revision date
"""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

import pytest

from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import instantiate_test_transformer
from tests.integration.pipelines.observability import build_test_logger


# YYYY-MM-DD pattern
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Date fields that must follow YYYY-MM-DD format when present
PUBMED_DATE_FIELDS = [
    "publication_date",
    "pub_date",
    "epub_date",
    "accepted_date",
    "received_date",
    "revised_date",
]


@pytest.fixture
def transformer() -> PubMedPublicationTransformer:
    """Create PubMed transformer with minimal dependencies."""
    return instantiate_test_transformer(
        PubMedPublicationTransformer,
        provider="pubmed",
    )


@pytest.fixture
def pipeline_context() -> PipelineContext:
    """Create a minimal pipeline context for transformation."""
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=build_test_logger(),
    )


def _make_pubmed_xml(
    pmid: str = "12345678",
    year: str = "2024",
    month: str | None = "03",
    day: str | None = "15",
    epub_year: str | None = None,
    epub_month: str | None = None,
    epub_day: str | None = None,
) -> str:
    """Generate PubMed XML for testing date extraction."""
    pub_date_parts = f"<Year>{year}</Year>"
    if month:
        pub_date_parts += f"<Month>{month}</Month>"
    if day:
        pub_date_parts += f"<Day>{day}</Day>"

    epub_section = ""
    if epub_year:
        epub_parts = f"<Year>{epub_year}</Year>"
        if epub_month:
            epub_parts += f"<Month>{epub_month}</Month>"
        if epub_day:
            epub_parts += f"<Day>{epub_day}</Day>"
        epub_section = f"""
        <ArticleDate DateType="Electronic">
            {epub_parts}
        </ArticleDate>
        """

    return f"""<?xml version="1.0"?>
    <PubmedArticle>
        <MedlineCitation>
            <PMID Version="1">{pmid}</PMID>
            <Article>
                <ArticleTitle>Test Article</ArticleTitle>
                <Journal>
                    <Title>Test Journal</Title>
                    <JournalIssue>
                        <PubDate>
                            {pub_date_parts}
                        </PubDate>
                    </JournalIssue>
                </Journal>
                {epub_section}
            </Article>
        </MedlineCitation>
    </PubmedArticle>
    """


@pytest.mark.integration
class TestPubMedDateNormalization:
    """Integration tests for PubMed date normalization."""

    @pytest.mark.asyncio
    async def test_med_date_normalization__date_format__5103afd1(
        self,
        transformer: PubMedPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Publication_date field must be YYYY-MM-DD format."""
        xml = _make_pubmed_xml(year="2024", month="03", day="15")
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        assert pub_date is not None, "publication_date should not be None"
        assert DATE_PATTERN.match(pub_date), (
            f"Invalid date format: {pub_date}, expected YYYY-MM-DD"
        )

    @pytest.mark.asyncio
    async def test_pipelines_pubmed_date_normalization_136__98d0afcc(
        self,
        transformer: PubMedPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """All date fields must be YYYY-MM-DD format or None."""
        xml = _make_pubmed_xml(
            year="2024",
            month="03",
            day="15",
            epub_year="2024",
            epub_month="02",
            epub_day="28",
        )
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(pipeline_context, record, 0)

        for field in PUBMED_DATE_FIELDS:
            value = result.get(field)
            if value is not None:
                assert DATE_PATTERN.match(value), (
                    f"Invalid {field} format: {value}, expected YYYY-MM-DD"
                )

    @pytest.mark.asyncio
    async def test_med_date_normalization__only_normalization__f40aa689(
        self,
        transformer: PubMedPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Year-only dates should be normalized to YYYY-12-31."""
        xml = _make_pubmed_xml(year="2024", month=None, day=None)
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        assert pub_date == "2024-12-31", (
            f"Year-only date should normalize to YYYY-12-31, got {pub_date}"
        )

    @pytest.mark.asyncio
    async def test_med_date_normalization__month_normalization__c40dff7b(
        self,
        transformer: PubMedPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Year-month dates should be normalized to the last day of month."""
        xml = _make_pubmed_xml(year="2024", month="02", day=None)
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        assert pub_date == "2024-02-29", (
            f"Year-month date should normalize to month end, got {pub_date}"
        )

    @pytest.mark.asyncio
    async def test_epub_date_takes_priority(
        self,
        transformer: PubMedPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Full epub_date should take priority over pub_date."""
        xml = _make_pubmed_xml(
            year="2024",
            month="06",
            day="15",
            epub_year="2024",
            epub_month="03",
            epub_day="01",
        )
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(pipeline_context, record, 0)

        pub_date = result.get("publication_date")
        # epub_date (2024-03-01) should take priority
        assert pub_date == "2024-03-01", (
            f"Expected epub_date to take priority, got {pub_date}"
        )

    @pytest.mark.asyncio
    async def test_year_field_is_integer(
        self,
        transformer: PubMedPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """publication_year field should be an integer."""
        xml = _make_pubmed_xml(year="2024", month="03", day="15")
        record: dict[str, Any] = {"_raw_xml": xml}

        result = await transformer.transform(pipeline_context, record, 0)

        year = result.get("publication_year")
        assert year is not None
        assert isinstance(year, int), (
            f"publication_year should be int, got {type(year)}"
        )
        assert 1500 <= year <= 2100, f"publication_year out of valid range: {year}"


@pytest.mark.unit
class TestPubMedDateEdgeCases:
    """Edge case tests for PubMed date handling."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        """Create PubMed transformer."""
        return instantiate_test_transformer(
            PubMedPublicationTransformer,
            provider="pubmed",
        )

    @pytest.mark.parametrize(
        "epub_date,pub_date,year,expected_pattern",
        [
            # Full epub_date (10+ chars) - use epub
            ("2024-03-15", "2024-04-01", 2024, r"^2024-03-15$"),
            # Partial epub (< 10 chars) - fall back to pub_date
            ("2024-03", "2024-04-15", 2024, r"^2024-04-15$"),
            # No epub, full pub_date
            (None, "2024-03-15", 2024, r"^2024-03-15$"),
            # No epub, partial pub_date (YYYY-MM)
            (None, "2024-06", 2024, r"^2024-06-30$"),
            # No epub, no pub_date - use year
            (None, None, 2024, r"^2024-12-31$"),
            # All None
            (None, None, None, None),
        ],
    )
    def test_date_priority_combinations(
        self,
        transformer: PubMedPublicationTransformer,
        epub_date: str | None,
        pub_date: str | None,
        year: int | None,
        expected_pattern: str | None,
    ) -> None:
        """Test date priority: epub > pub > year."""
        result = transformer._compute_publication_date(epub_date, pub_date, year)

        if expected_pattern is None:
            assert result is None
        else:
            assert result is not None
            assert re.match(expected_pattern, result), (
                f"Expected {expected_pattern}, got {result}"
            )
