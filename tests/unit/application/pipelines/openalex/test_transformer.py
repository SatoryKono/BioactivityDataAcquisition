"""Unit tests for OpenAlex Publication Transformer.

Tests the OpenAlexPublicationTransformer class.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexPublicationTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.fixture
def transformer() -> OpenAlexPublicationTransformer:
    """Create a transformer instance for testing."""
    return OpenAlexPublicationTransformer()


@pytest.fixture
def pipeline_context() -> PipelineContext:
    """Create a pipeline context for testing."""
    return PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
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
        "cited_by_count": 42,
        "concepts": [
            {"display_name": "Chemistry", "score": 0.9},
            {"display_name": "Biology", "score": 0.7},
        ],
        "language": "en",
        "_lookup_method": "doi",
    }


class TestOpenAlexPublicationTransformer:
    """Tests for OpenAlexPublicationTransformer."""

    @pytest.mark.asyncio
    async def test_transform_basic_record(
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
        assert result["year"] == 2024
        assert result["publication_date"] == "2024-05-15"
        assert result["doc_type"] == "PUBLICATION"
        assert result["abstract"] == "This is an abstract"
        assert result["journal"] == "Nature"
        assert result["issn"] == "0028-0836"
        assert result["publisher"] == "Springer Nature"
        assert result["is_oa"] is True
        assert result["oa_status"] == "gold"
        assert result["cited_by_count"] == 42
        assert result["language"] == "en"
        assert result["source"] == "openalex"
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
    async def test_transform_record_without_id_returns_none(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Should return None for record without OpenAlex ID."""
        record = {
            "id": None,
            "title": "Record Without ID",
        }

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is None

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
            "_original_doi": "10.1016/j.invalid.doi",
        }

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["_lookup_method"] == "title_fallback"
        assert result["_original_doi"] == "10.1016/j.invalid.doi"

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
        assert result["year"] is None  # Filtered out

    @pytest.mark.asyncio
    async def test_transform_doc_type_mapping(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Should map OpenAlex types to internal types."""
        test_cases = [
            ("article", "PUBLICATION"),
            ("preprint", "PREPRINT"),
            ("book-chapter", "PUBLICATION"),
            ("dataset", "DATASET"),
            ("unknown_type", "PUBLICATION"),  # Default
        ]

        for openalex_type, expected_type in test_cases:
            record = {
                "id": "https://openalex.org/W1234567890",
                "title": "Test",
                "type": openalex_type,
            }
            result = await transformer.transform(pipeline_context, record, 0)
            assert result is not None
            assert result["doc_type"] == expected_type

    @pytest.mark.asyncio
    async def test_transform_concepts_extraction(
        self,
        transformer: OpenAlexPublicationTransformer,
        pipeline_context: PipelineContext,
    ) -> None:
        """Should extract concepts from record."""
        record = {
            "id": "https://openalex.org/W1234567890",
            "title": "Test",
            "concepts": [
                {"display_name": "Chemistry"},
                {"display_name": "Biology"},
            ],
        }

        result = await transformer.transform(pipeline_context, record, 0)

        assert result is not None
        assert result["concepts"] == ["Chemistry", "Biology"]

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
    async def test_transform_generates_content_hash(
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
    async def test_transform_generates_entity_id(
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
    async def test_transform_adds_lineage_fields(
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
        assert result["_run_type"] == "incremental"
        assert result["_index"] == 0
