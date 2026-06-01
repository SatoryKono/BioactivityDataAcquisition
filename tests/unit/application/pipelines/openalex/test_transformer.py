"""Unit tests for OpenAlex Publication Transformer.

Tests the OpenAlexPublicationTransformer class.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import json
import pytest

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexPublicationTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.helpers.transformer_dependencies import instantiate_test_transformer

LEGACY_HTTP_DOI = "http" + "://doi.org/10.1038/NATURE12373"
pytestmark = pytest.mark.usefixtures("publication_type_classification_data")


@pytest.fixture
def transformer() -> OpenAlexPublicationTransformer:
    """Create a transformer instance for testing."""
    return instantiate_test_transformer(OpenAlexPublicationTransformer)


@pytest.fixture
def pipeline_context() -> PipelineContext:
    """Create a pipeline context for testing."""
    return PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        logger=NoOpLogger(),
    )


@pytest.fixture
def sample_openalex_record() -> dict[str, Any]:
    """Sample OpenAlex Works record for testing."""
    return {
        "id": "https://openalex.org/W2148763428",
        "doi": "https://doi.org/10.1038/s41586-024-07487-w",
        "title": "Example Publication Title",
        "publication_year": 2024,
        "publication_date": "2024-05-15",
        "type": "article",
        "type_crossref": "journal-article",
        "abstract_inverted_index": {
            "This": [0],
            "is": [1],
            "an": [2],
            "abstract": [3],
        },
        "authorships": [
            {"author": {"display_name": "John Doe", "id": "A123"}},
            {"author": {"display_name": "Jane Smith", "id": "A456"}},
        ],
        "primary_location": {
            "source": {
                "display_name": "Nature",
                "issn_l": "0028-0836",
                "host_organization_name": "Springer Nature",
            }
        },
        "open_access": {
            "is_oa": True,
            "oa_status": "gold",
        },
        # Note: OpenAlex API returns cited_by_count, transformed to citations_received
        "cited_by_count": 42,  # Source field name from OpenAlex API
        "language": "en",
        "_lookup_method": "doi",
    }


class TestOpenAlexPublicationTransformer:
    """Tests for OpenAlexPublicationTransformer."""

    @pytest.mark.asyncio
    async def test_transformer__basic_record__c27c8b6d(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
        sample_openalex_record: dict[str, Any],
    ) -> None:
        """Should transform a basic OpenAlex record to Silver format."""
        result = await transformer.transform(
            pipeline_context, sample_openalex_record, 0
        )

        assert result is not None
        assert result["openalex_id"] == "W2148763428"
        assert result["doi"] == "10.1038/s41586-024-07487-w"
        assert result["title"] == "Example Publication Title"
        assert result["publication_year"] == 2024
        assert result["publication_date"] == "2024-05-15"
        assert result["publication_type"] == "article"
        assert result["type_crossref"] == "journal-article"
        assert result["publication_type_unified"] == "Journal Article"
        assert result["abstract"] == "This is an abstract"
        assert result["journal"] == "Nature"
        assert result["issn"] == "0028-0836"
        assert result["issn_list"] == '["0028-0836"]'
        assert result["publisher"] == "Springer Nature"
        assert result["is_oa"] is True
        assert result["oa_status"] == "gold"
        assert result["citations_received"] == 42  # Unified field name
        assert result["language"] == "en"
        assert result["_source"] == "openalex"
        assert result["_lookup_method"] == "doi"

    @pytest.mark.asyncio
    async def test_transform_record_without_doi(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Should transform record without DOI (title-only lookup)."""
        record = {
            "id": "https://openalex.org/W9876543210",
            "doi": None,
            "title": "Title Without DOI",
            "publication_year": 2023,
            "_lookup_method": "title_only",
        }

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["openalex_id"] == "W9876543210"
        assert result["doi"] is None
        assert result["title"] == "Title Without DOI"
        assert result["_lookup_method"] == "title_only"

    @pytest.mark.asyncio
    async def test_transform_uses_awards_for_grants_field(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
        sample_openalex_record: dict[str, Any],
    ) -> None:
        """Should populate grants from current OpenAlex awards field."""
        sample_openalex_record["awards"] = [
            {
                "id": "https://openalex.org/G5453342221",
                "display_name": "Fusion roadmap implementation",
                "funder_award_id": "633053",
                "funder_id": "https://openalex.org/F4320337670",
                "funder_display_name": "H2020 Euratom",
            }
        ]

        result = await transformer.transform(
            pipeline_context,
            sample_openalex_record,
            0,
        )

        assert result is not None
        grants = json.loads(result["grants"])
        assert grants[0]["award_id"] == "633053"
        assert grants[0]["award_openalex_id"] == "G5453342221"
        assert grants[0]["funder"] == "F4320337670"

    @pytest.mark.asyncio
    async def test_transform_record_without_id_raises_filtered_out_error(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Missing OpenAlex ID must use runtime filtered-out disposition."""
        record = {
            "id": None,
            "title": "Record Without ID",
        }

        with pytest.raises(FilteredOutError, match="primary identifier"):
            await transformer.transform(pipeline_context, record, 0)

    @pytest.mark.asyncio
    async def test_transform_with_fallback_lookup(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Should preserve fallback lookup metadata."""
        record = {
            "id": "https://openalex.org/W1234567890",
            "doi": "https://doi.org/10.1016/j.cell.2024.01.005",
            "title": "Fallback Title",
            "_lookup_method": "title_fallback",
            "_original_id": "10.1016/j.invalid.doi",
        }

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["_lookup_method"] == "title_fallback"
        assert result["_original_id"] == "10.1016/j.invalid.doi"

    @pytest.mark.asyncio
    async def test_transform_invalid_year_is_filtered(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Should filter out invalid publication years."""
        record = {
            "id": "https://openalex.org/W1234567890",
            "title": "Invalid Year",
            "publication_year": 1400,  # Invalid: before 1500
        }

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["publication_year"] is None  # Filtered out

    @pytest.mark.asyncio
    async def test_transform_type_normalized(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Should preserve OpenAlex type while deriving unified classification."""
        test_cases = [
            ("article", "article", "Journal Article"),
            ("preprint", "preprint", "Preprint"),
            ("book-chapter", "book-chapter", "Book Chapter"),
            ("dataset", "dataset", "Dataset"),
            ("unknown_type", "unknown_type", None),
        ]

        for openalex_type, expected_raw, expected_unified in test_cases:
            record = {
                "id": "https://openalex.org/W1234567890",
                "title": "Test",
                "type": openalex_type,
            }
            result = await transformer.transform(pipeline_context, record, 0)
            assert result is not None
            assert result["publication_type"] == expected_raw
            assert result["publication_type_unified"] == expected_unified

    @pytest.mark.asyncio
    async def test_transform_empty_abstract_inverted_index(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Should handle empty abstract inverted index."""
        record = {
            "id": "https://openalex.org/W1234567890",
            "title": "Test",
            "abstract_inverted_index": {},
        }

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["abstract"] is None

    @pytest.mark.asyncio
    async def test_transformer__content_hash__4847b1a3(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
        sample_openalex_record: dict[str, Any],
    ) -> None:
        """Should generate content hash for versioning."""
        result = await transformer.transform(
            pipeline_context, sample_openalex_record, 0
        )

        assert result is not None
        assert "content_hash" in result
        assert len(result["content_hash"]) == 64  # SHA256 hex

    @pytest.mark.asyncio
    async def test_transformer__generates_entity_id__4cb30425(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
        sample_openalex_record: dict[str, Any],
    ) -> None:
        """Should generate entity ID."""
        result = await transformer.transform(
            pipeline_context, sample_openalex_record, 0
        )

        assert result is not None
        assert "entity_id" in result
        assert "openalex" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transformer__adds_lineage_fields__9f092bf4(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
        sample_openalex_record: dict[str, Any],
    ) -> None:
        """Should add lineage fields from context."""
        result = await transformer.transform(
            pipeline_context, sample_openalex_record, 0
        )

        assert result is not None
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result
        assert "_index" in result
        assert "_run_type" in result
        assert result["_index"] == 0

    @pytest.mark.asyncio
    async def test_transform_affiliation_list_serialized(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Should serialize affiliation_list as JSON string."""
        record = {
            "id": "https://openalex.org/W1234567890",
            "title": "Affiliation Test",
            "_lookup_method": "doi",
            "authorships": [
                {"institutions": [{"display_name": "MIT"}]},
                {
                    "institutions": [
                        {"display_name": "Stanford"},
                        {"display_name": "MIT"},
                    ]
                },
            ],
        }

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        # Deserialize JSON to compare data (not format)
        assert json.loads(result["affiliation_list"]) == ["MIT", "Stanford"]

    @pytest.mark.asyncio
    async def test_transform_affiliation_list_empty(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Should return None for empty affiliation_list (no affiliations)."""
        record = {
            "id": "https://openalex.org/W1234567891",
            "title": "Empty Affiliation Test",
            "_lookup_method": "doi",
            "authorships": [],
        }

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        # Empty affiliations list → None (not "[]") per serialize_json design
        assert result["affiliation_list"] is None


class TestOpenAlexDoiNormalization:
    """Tests for DOI normalization in OpenAlex transformer."""

    @pytest.fixture
    def transformer(self) -> OpenAlexPublicationTransformer:
        """Create a transformer instance for testing."""
        return instantiate_test_transformer(OpenAlexPublicationTransformer)

    @staticmethod
    def _make_record_with_doi(doi_url: str | None) -> dict[str, Any]:
        """Create an OpenAlex record with a specific DOI URL."""
        return {
            "id": "https://openalex.org/W2148763428",
            "doi": doi_url,
            "title": "DOI Normalization Test",
            "_lookup_method": "doi",
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "raw_doi_url,expected",
        [
            # Uppercase DOIs should be lowercased
            ("https://doi.org/10.1038/NATURE12373", "10.1038/nature12373"),
            # Already lowercase should stay the same
            ("https://doi.org/10.1038/nature12373", "10.1038/nature12373"),
            # Mixed case
            ("https://doi.org/10.1000/ABC.DEF", "10.1000/abc.def"),
            ("https://doi.org/10.1000/Test-DOI_123", "10.1000/test-doi_123"),
            # HTTP prefix
            (LEGACY_HTTP_DOI, "10.1038/nature12373"),
            # doi: prefix
            ("doi:10.1038/NATURE12373", "10.1038/nature12373"),
            # Bare DOI (no prefix)
            ("10.1038/NATURE12373", "10.1038/nature12373"),
        ],
    )
    async def test_doi_normalization_lowercase_and_strip(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
        raw_doi_url: str,
        expected: str,
    ) -> None:
        """Test that DOIs are normalized to lowercase and stripped."""
        record = self._make_record_with_doi(raw_doi_url)

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["doi"] == expected

    @pytest.mark.asyncio
    async def test_doi_normalization_none_handling(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test that None DOI remains None."""
        record = self._make_record_with_doi(None)

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["doi"] is None

    @pytest.mark.asyncio
    async def test_doi_normalization_affects_content_hash(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test that DOIs with different cases produce same content hash after normalization."""
        record_upper = self._make_record_with_doi("https://doi.org/10.1038/NATURE12373")
        record_lower = self._make_record_with_doi("https://doi.org/10.1038/nature12373")

        result_upper = await transformer.transform(pipeline_context, record_upper, 0)
        result_lower = await transformer.transform(pipeline_context, record_lower, 0)

        assert result_upper is not None
        assert result_lower is not None
        # After normalization, content hashes should be identical
        assert result_upper["content_hash"] == result_lower["content_hash"]


class TestOpenAlexPublicationDateNormalization:
    """Tests for publication_date normalization in OpenAlex transformer."""

    @pytest.fixture
    def transformer(self) -> OpenAlexPublicationTransformer:
        """Create a transformer instance for testing."""
        return instantiate_test_transformer(OpenAlexPublicationTransformer)

    @staticmethod
    def _make_record_with_date(pub_date: str | None) -> dict[str, Any]:
        """Create an OpenAlex record with a specific publication_date."""
        return {
            "id": "https://openalex.org/W2148763428",
            "title": "Publication Date Normalization Test",
            "publication_date": pub_date,
            "_lookup_method": "doi",
        }

    @pytest.mark.asyncio
    async def test_full_date_unchanged(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test that full ISO date (YYYY-MM-DD) is returned unchanged."""
        record = self._make_record_with_date("2024-05-15")

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["publication_date"] == "2024-05-15"

    @pytest.mark.asyncio
    async def test_partial_date_month_normalized_to_end(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test that YYYY-MM is normalized to the last day of month."""
        record = self._make_record_with_date("2024-02")

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["publication_date"] == "2024-02-29"

    @pytest.mark.asyncio
    async def test_partial_date_year_normalized_to_end(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test that YYYY is normalized to YYYY-12-31 (end of year)."""
        record = self._make_record_with_date("2024")

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["publication_date"] == "2024-12-31"

    @pytest.mark.asyncio
    async def test_none_date_remains_none(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test that None publication_date remains None."""
        record = self._make_record_with_date(None)

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["publication_date"] is None

    @pytest.mark.asyncio
    async def test_empty_string_becomes_none(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test that empty string publication_date becomes None."""
        record = self._make_record_with_date("")

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["publication_date"] is None

    @pytest.mark.asyncio
    async def test_whitespace_date_becomes_none(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test that whitespace-only publication_date becomes None."""
        record = self._make_record_with_date("   ")

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["publication_date"] is None

    @pytest.mark.asyncio
    async def test_invalid_format_becomes_none(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Test that invalid date format becomes None."""
        record = self._make_record_with_date("15-05-2024")  # DD-MM-YYYY format

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["publication_date"] is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "raw_date,expected",
        [
            ("2024-01-15", "2024-01-15"),  # Full date
            ("2024-01", "2024-01-31"),  # Month precision
            ("2024", "2024-12-31"),  # Year precision
            ("1999-12", "1999-12-31"),  # Old date, month precision
            ("1999", "1999-12-31"),  # Old date, year precision
        ],
    )
    async def test_various_date_formats(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
        raw_date: str,
        expected: str,
    ) -> None:
        """Test various date format normalizations."""
        record = self._make_record_with_date(raw_date)

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["publication_date"] == expected
