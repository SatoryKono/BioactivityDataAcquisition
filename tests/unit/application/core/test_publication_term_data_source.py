"""Unit tests for PublicationTermDataSource wrapper."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from bioetl.application.core.publication_term_data_source import (
    PublicationTermDataSource,
)
from bioetl.domain.types import HealthStatus


class MockDataSource:
    """Mock data source for testing PublicationTermDataSource wrapper.

    Tracks method calls for test assertions.
    """

    provider_name = "chembl"

    def __init__(self, documents: list[dict] | None = None):
        """Initialize with optional list of document records."""
        self._documents = documents or []
        self.fetch_calls: list[dict[str, object]] = []
        self.__aenter__ = AsyncMock(return_value=self)
        self.__aexit__ = AsyncMock(return_value=None)
        self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        self.aclose = AsyncMock()

    async def fetch(self, entity_type: str, **kwargs):
        """Yield configured documents."""
        await asyncio.sleep(0)
        self.fetch_calls.append({"entity_type": entity_type, **kwargs})
        for doc in self._documents:
            yield doc


# Sample document records for testing
SAMPLE_DOCUMENT_WITH_TERMS = {
    "publication_id": "CHEMBL1123456",
    "title": "Test Document",
    "mesh_terms": [
        {
            "mesh_heading": "Enzyme Inhibitors",
            "mesh_id": "D004791",
            "mesh_qualifier": "therapeutic use",
        },
        {
            "mesh_heading": "Protein Kinases",
            "mesh_id": "D011494",
            "mesh_qualifier": None,
        },
    ],
    "keywords": ["kinase", "inhibitor", "cancer"],
}

SAMPLE_DOCUMENT_EMPTY_TERMS = {
    "publication_id": "CHEMBL9999999",
    "title": "Document without terms",
    "mesh_terms": [],
    "keywords": [],
}

SAMPLE_DOCUMENT_NO_TERMS = {
    "publication_id": "CHEMBL8888888",
    "title": "Document with no term fields",
    # No mesh_terms or keywords fields at all
}

SAMPLE_DOCUMENT_INVALID_MESH = {
    "publication_id": "CHEMBL7777777",
    "title": "Document with invalid mesh",
    "mesh_terms": ["invalid", None, 123],  # Not dicts
    "keywords": ["valid_keyword"],
}


@pytest.fixture
def mock_data_source():
    """Create a mock data source with sample documents."""
    return MockDataSource(
        documents=[
            SAMPLE_DOCUMENT_WITH_TERMS,
            SAMPLE_DOCUMENT_EMPTY_TERMS,
        ]
    )


@pytest.fixture
def mock_data_source_no_documents():
    """Create a mock data source with no documents."""
    return MockDataSource(documents=[])


@pytest.fixture
def mock_data_source_single_document():
    """Create a mock data source with a single document."""
    return MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])


@pytest.mark.unit
class TestPublicationTermDataSourceInit:
    """Tests for PublicationTermDataSource initialization."""

    def test_initialization(self, mock_data_source):
        """Test PublicationTermDataSource initializes correctly."""
        wrapper = PublicationTermDataSource(data_source=mock_data_source)

        assert wrapper.provider_name == "chembl"
        assert wrapper._data_source is mock_data_source

    def test_provider_name_from_wrapped(self, mock_data_source):
        """Test provider_name is delegated to wrapped data source."""
        mock_data_source.provider_name = "pubchem"
        wrapper = PublicationTermDataSource(data_source=mock_data_source)

        assert wrapper.provider_name == "pubchem"

    def test_entity_type_constants(self):
        """Test entity type constants are set correctly."""
        assert PublicationTermDataSource.SOURCE_ENTITY_TYPE == "publication"
        assert PublicationTermDataSource.TARGET_ENTITY_TYPE == "publication_term"


@pytest.mark.unit
class TestPublicationTermDataSourceContextManager:
    """Tests for async context manager behavior."""

    @pytest.mark.asyncio
    async def test_aenter_delegates(self, mock_data_source):
        """Test __aenter__ delegates to wrapped data source."""
        wrapper = PublicationTermDataSource(data_source=mock_data_source)

        result = await wrapper.__aenter__()

        assert result is wrapper
        mock_data_source.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_aexit_delegates(self, mock_data_source):
        """Test __aexit__ delegates to wrapped data source."""
        wrapper = PublicationTermDataSource(data_source=mock_data_source)

        await wrapper.__aexit__(None, None, None)

        mock_data_source.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_context_manager_full_cycle(self, mock_data_source):
        """Test using PublicationTermDataSource as async context manager."""
        wrapper = PublicationTermDataSource(data_source=mock_data_source)

        async with wrapper as w:
            assert w is wrapper

        mock_data_source.__aenter__.assert_called_once()
        mock_data_source.__aexit__.assert_called_once()


@pytest.mark.unit
class TestPublicationTermDataSourceFetch:
    """Tests for fetch method."""

    @pytest.mark.asyncio
    async def test_fetch_publication_term_extracts_terms(
        self, mock_data_source_single_document
    ):
        """Test fetch('publication_term') extracts terms from documents."""
        wrapper = PublicationTermDataSource(
            data_source=mock_data_source_single_document
        )

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        # Expected: 2 MESH_HEADING + 1 MESH_QUALIFIER + 3 KEYWORD = 6 terms
        assert len(terms) == 6

        # Check term types
        term_types = [t["term_type"] for t in terms]
        assert term_types.count("MESH_HEADING") == 2
        assert term_types.count("MESH_QUALIFIER") == 1
        assert term_types.count("KEYWORD") == 3

    @pytest.mark.asyncio
    async def test_fetch_publication_term_with_limit(
        self, mock_data_source_single_document
    ):
        """Test fetch('publication_term') respects limit parameter."""
        wrapper = PublicationTermDataSource(
            data_source=mock_data_source_single_document
        )

        terms = []
        async for term in wrapper.fetch("publication_term", limit=3):
            terms.append(term)

        assert len(terms) == 3

    @pytest.mark.asyncio
    async def test_fetch_other_entity_delegates(self, mock_data_source):
        """Test fetch for other entity types delegates to wrapped adapter."""
        wrapper = PublicationTermDataSource(data_source=mock_data_source)

        records = []
        async for record in wrapper.fetch("document"):
            records.append(record)

        # Should get the original documents, not terms
        assert len(records) == 2
        assert all("publication_id" in r for r in records)

    @pytest.mark.asyncio
    async def test_fetch_other_entity_forwards_offset(self, mock_data_source):
        """Test non-target fetch forwards offset to wrapped adapter."""
        wrapper = PublicationTermDataSource(data_source=mock_data_source)

        async for _ in wrapper.fetch("document", offset=25):
            pass

        assert mock_data_source.fetch_calls[-1]["entity_type"] == "document"
        assert mock_data_source.fetch_calls[-1]["offset"] == 25

    @pytest.mark.asyncio
    async def test_fetch_publication_term_empty_result(
        self, mock_data_source_no_documents
    ):
        """Test fetch('publication_term') with no documents yields nothing."""
        wrapper = PublicationTermDataSource(data_source=mock_data_source_no_documents)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        assert len(terms) == 0


@pytest.mark.unit
class TestPublicationTermDataSourceTermExtraction:
    """Tests for term extraction logic."""

    @pytest.mark.asyncio
    async def test_extract_mesh_headings(self):
        """Test MeSH heading extraction."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            if term["term_type"] == "MESH_HEADING":
                terms.append(term)

        assert len(terms) == 2
        assert any(t["term"] == "Enzyme Inhibitors" for t in terms)
        assert any(t["term"] == "Protein Kinases" for t in terms)

    @pytest.mark.asyncio
    async def test_extract_mesh_qualifiers(self):
        """Test MeSH qualifier extraction as separate terms."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            if term["term_type"] == "MESH_QUALIFIER":
                terms.append(term)

        assert len(terms) == 1
        assert terms[0]["term"] == "therapeutic use"

    @pytest.mark.asyncio
    async def test_extract_keywords(self):
        """Test keyword extraction."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            if term["term_type"] == "KEYWORD":
                terms.append(term)

        assert len(terms) == 3
        term_values = [t["term"] for t in terms]
        assert "kinase" in term_values
        assert "inhibitor" in term_values
        assert "cancer" in term_values

    @pytest.mark.asyncio
    async def test_skip_empty_terms(self):
        """Test that empty terms are skipped."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_EMPTY_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        assert len(terms) == 0

    @pytest.mark.asyncio
    async def test_skip_missing_term_fields(self):
        """Test that documents without term fields are handled gracefully."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_NO_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        assert len(terms) == 0

    @pytest.mark.asyncio
    async def test_skip_invalid_mesh_entries(self):
        """Test that invalid mesh entries (non-dicts) are skipped."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_INVALID_MESH])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        # Should only get the valid keyword
        assert len(terms) == 1
        assert terms[0]["term"] == "valid_keyword"


@pytest.mark.unit
class TestPublicationTermDataSourceRecordFormat:
    """Tests for term record format and entity_id computation."""

    @pytest.mark.asyncio
    async def test_term_record_fields(self):
        """Test that term records have all required fields."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        for term in terms:
            assert "entity_id" in term
            assert "publication_id" in term
            assert "term" in term
            assert "term_type" in term
            assert "mesh_id" in term
            assert "qualifier" in term

    @pytest.mark.asyncio
    async def test_entity_id_computed(self):
        """Test that entity_id is computed for each term."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        # All entity_ids should be 16-char hex strings
        for term in terms:
            assert len(term["entity_id"]) == 16
            assert all(c in "0123456789abcdef" for c in term["entity_id"])

    @pytest.mark.asyncio
    async def test_entity_id_uniqueness(self):
        """Test that entity_ids are unique for different terms."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        entity_ids = [t["entity_id"] for t in terms]
        assert len(entity_ids) == len(set(entity_ids)), "Entity IDs should be unique"

    @pytest.mark.asyncio
    async def test_entity_id_deterministic(self):
        """Test that entity_id is deterministic for same inputs."""
        source1 = MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        source2 = MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper1 = PublicationTermDataSource(data_source=source1)
        wrapper2 = PublicationTermDataSource(data_source=source2)

        terms1 = []
        async for term in wrapper1.fetch("publication_term"):
            terms1.append(term)

        terms2 = []
        async for term in wrapper2.fetch("publication_term"):
            terms2.append(term)

        # Same inputs should produce same entity_ids
        ids1 = [t["entity_id"] for t in terms1]
        ids2 = [t["entity_id"] for t in terms2]
        assert ids1 == ids2

    @pytest.mark.asyncio
    async def test_mesh_id_preserved(self):
        """Test that mesh_id is preserved in term records."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            if term["term_type"] == "MESH_HEADING":
                terms.append(term)

        # First mesh heading should have mesh_id
        enzyme_term = next(t for t in terms if t["term"] == "Enzyme Inhibitors")
        assert enzyme_term["mesh_id"] == "D004791"


@pytest.mark.unit
class TestPublicationTermDataSourceDelegation:
    """Tests for method delegation to wrapped data source."""

    @pytest.mark.asyncio
    async def test_health_check_delegates(self, mock_data_source):
        """Test health_check delegates to wrapped data source."""
        wrapper = PublicationTermDataSource(data_source=mock_data_source)

        result = await wrapper.health_check()

        assert result == HealthStatus.HEALTHY
        mock_data_source.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_delegates(self, mock_data_source):
        """Test aclose delegates to wrapped data source."""
        wrapper = PublicationTermDataSource(data_source=mock_data_source)

        await wrapper.aclose()

        mock_data_source.aclose.assert_called_once()


@pytest.mark.unit
class TestPublicationTermDataSourceEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_document_without_chembl_id_skipped(self):
        """Test documents without publication_id are skipped."""
        source = MockDataSource(
            documents=[
                {"title": "No ID document", "mesh_terms": [], "keywords": ["test"]}
            ]
        )
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        assert len(terms) == 0

    @pytest.mark.asyncio
    async def test_whitespace_keywords_stripped(self):
        """Test that whitespace in keywords is stripped."""
        source = MockDataSource(
            documents=[
                {
                    "publication_id": "CHEMBL1",
                    "keywords": ["  spaced  ", "\ttabbed\t", "  ", ""],
                    "mesh_terms": [],
                }
            ]
        )
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        # Only non-empty after stripping
        assert len(terms) == 2
        assert terms[0]["term"] == "spaced"
        assert terms[1]["term"] == "tabbed"

    @pytest.mark.asyncio
    async def test_multiple_documents_combined(self):
        """Test that terms from multiple documents are combined."""
        source = MockDataSource(
            documents=[
                {
                    "publication_id": "CHEMBL1",
                    "keywords": ["term1"],
                    "mesh_terms": [],
                },
                {
                    "publication_id": "CHEMBL2",
                    "keywords": ["term2"],
                    "mesh_terms": [],
                },
            ]
        )
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch("publication_term"):
            terms.append(term)

        assert len(terms) == 2
        doc_ids = {t["publication_id"] for t in terms}
        assert doc_ids == {"CHEMBL1", "CHEMBL2"}

    @pytest.mark.asyncio
    async def test_filter_ids_passed_to_wrapped(self):
        """Test that filter_ids parameter is passed to wrapped adapter."""
        call_args = {}

        class TrackingMockDataSource(MockDataSource):
            async def fetch(self, entity_type: str, **kwargs):
                call_args.update(kwargs)
                call_args["entity_type"] = entity_type
                async for doc in super().fetch(entity_type, **kwargs):
                    yield doc

        source = TrackingMockDataSource(
            documents=[
                {
                    "publication_id": "CHEMBL1",
                    "keywords": ["test"],
                    "mesh_terms": [],
                }
            ]
        )
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch(
            "publication_term",
            filter_ids=["CHEMBL1", "CHEMBL2"],
            filter_field="publication_id",
        ):
            terms.append(term)

        # Verify fetch was called with publication entity type (ADR-024 naming)
        assert call_args["entity_type"] == "publication"
        assert call_args["filter_ids"] == ["CHEMBL1", "CHEMBL2"]
        assert call_args["filter_field"] == "publication_id"


class MockFilterableDataSource:
    """Mock data source that implements FilterableDataSourcePort."""

    provider_name = "chembl"

    def __init__(self, documents: list[dict] | None = None):
        self._documents = documents or []
        self.__aenter__ = AsyncMock(return_value=self)
        self.__aexit__ = AsyncMock(return_value=None)
        self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        self.aclose = AsyncMock()

    async def fetch(self, entity_type: str, **kwargs):
        await asyncio.sleep(0)
        for doc in self._documents:
            yield doc

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ):
        await asyncio.sleep(0)
        for doc in self._documents:
            yield doc

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ):
        await asyncio.sleep(0)
        for doc in self._documents:
            yield doc

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ):
        await asyncio.sleep(0)
        for doc in self._documents:
            yield doc


from bioetl.domain.ports import FilterableDataSourcePort

assert isinstance(MockFilterableDataSource(), FilterableDataSourcePort)


@pytest.mark.unit
class TestPublicationTermFilterable:
    """Tests for FilterableDataSourcePort methods."""

    @pytest.mark.asyncio
    async def test_fetch_filtered_publication_term(self):
        """Test fetch_filtered extracts terms from filtered publications."""
        source = MockFilterableDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch_filtered(
            entity_type="publication_term",
            filter_ids=["CHEMBL1123456"],
            filter_field="publication_id",
        ):
            terms.append(term)

        assert len(terms) == 6

    @pytest.mark.asyncio
    async def test_fetch_filtered_other_entity_delegates(self):
        """Test fetch_filtered delegates for non-term entity types."""
        source = MockFilterableDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_filtered(
            entity_type="document",
            filter_ids=["CHEMBL1123456"],
            filter_field="publication_id",
        ):
            records.append(record)

        assert len(records) == 1
        assert "publication_id" in records[0]

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_limit(self):
        """Test fetch_filtered respects limit for terms."""
        source = MockFilterableDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch_filtered(
            entity_type="publication_term",
            filter_ids=["CHEMBL1123456"],
            filter_field="publication_id",
            limit=2,
        ):
            terms.append(term)

        assert len(terms) == 2

    @pytest.mark.asyncio
    async def test_fetch_filtered_raises_for_non_filterable(self):
        """Test fetch_filtered raises TypeError for non-filterable adapter."""
        source = MockDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        with pytest.raises(
            TypeError, match="does not implement FilterableDataSourcePort"
        ):
            async for _ in wrapper.fetch_filtered(
                entity_type="publication_term",
                filter_ids=["CHEMBL1123456"],
                filter_field="publication_id",
            ):
                pass

    @pytest.mark.asyncio
    async def test_fetch_multi_filtered_publication_term(self):
        """Test fetch_multi_filtered extracts terms."""
        source = MockFilterableDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch_multi_filtered(
            entity_type="publication_term",
            filters={"publication_id": ["CHEMBL1123456"]},
        ):
            terms.append(term)

        assert len(terms) == 6

    @pytest.mark.asyncio
    async def test_fetch_multi_filtered_other_entity(self):
        """Test fetch_multi_filtered delegates for other entities."""
        source = MockFilterableDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_multi_filtered(
            entity_type="document",
            filters={"publication_id": ["CHEMBL1123456"]},
        ):
            records.append(record)

        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_multi_filtered_with_limit(self):
        """Test fetch_multi_filtered with limit."""
        source = MockFilterableDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch_multi_filtered(
            entity_type="publication_term",
            filters={"publication_id": ["CHEMBL1123456"]},
            limit=3,
        ):
            terms.append(term)

        assert len(terms) == 3

    @pytest.mark.asyncio
    async def test_fetch_multi_filtered_skips_no_chembl_id(self):
        """Test fetch_multi_filtered skips docs without publication_id."""
        source = MockFilterableDataSource(
            documents=[SAMPLE_DOCUMENT_NO_TERMS]  # Has no publication_id field
        )
        # Add publication_id to make it valid
        doc = {**SAMPLE_DOCUMENT_NO_TERMS}
        doc.pop("publication_id", None)
        source._documents = [{"title": "No ID", "keywords": ["test"], "mesh_terms": []}]
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch_multi_filtered(
            entity_type="publication_term",
            filters={"publication_id": ["CHEMBL1"]},
        ):
            terms.append(term)

        assert len(terms) == 0

    @pytest.mark.asyncio
    async def test_fetch_multi_filtered_raises_for_non_filterable(self):
        """Test fetch_multi_filtered raises TypeError."""
        source = MockDataSource()
        wrapper = PublicationTermDataSource(data_source=source)

        with pytest.raises(
            TypeError, match="does not implement FilterableDataSourcePort"
        ):
            async for _ in wrapper.fetch_multi_filtered(
                entity_type="publication_term",
                filters={"publication_id": ["CHEMBL1"]},
            ):
                pass

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_publication_term(self):
        """Test fetch_filtered_with_fallback extracts terms."""
        source = MockFilterableDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch_filtered_with_fallback(
            entity_type="publication_term",
            filter_ids=["CHEMBL1123456"],
            filter_field="publication_id",
            fallback_mapping={"CHEMBL1123456": "Test Document"},
        ):
            terms.append(term)

        assert len(terms) == 6

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_other_entity(self):
        """Test fetch_filtered_with_fallback delegates for other entities."""
        source = MockFilterableDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        records = []
        async for record in wrapper.fetch_filtered_with_fallback(
            entity_type="document",
            filter_ids=["CHEMBL1123456"],
            filter_field="publication_id",
            fallback_mapping={"CHEMBL1123456": "Test"},
        ):
            records.append(record)

        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_limit(self):
        """Test fetch_filtered_with_fallback respects limit."""
        source = MockFilterableDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        terms = []
        async for term in wrapper.fetch_filtered_with_fallback(
            entity_type="publication_term",
            filter_ids=["CHEMBL1123456"],
            filter_field="publication_id",
            fallback_mapping={"CHEMBL1123456": "Test"},
            limit=2,
        ):
            terms.append(term)

        assert len(terms) == 2

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_scales_upstream_limit(self):
        """Target fallback path should preserve publication expansion limit."""

        class _RecordingFilterableDataSource(MockFilterableDataSource):
            def __init__(self, documents: list[dict] | None = None):
                super().__init__(documents)
                self.fallback_calls: list[dict[str, object]] = []

            async def fetch_filtered_with_fallback(
                self,
                entity_type: str,
                filter_ids: list[str],
                filter_field: str,
                fallback_mapping: dict[str, str],
                limit: int | None = None,
            ):
                self.fallback_calls.append(
                    {
                        "entity_type": entity_type,
                        "filter_ids": filter_ids,
                        "filter_field": filter_field,
                        "fallback_mapping": fallback_mapping,
                        "limit": limit,
                    }
                )
                async for doc in super().fetch_filtered_with_fallback(
                    entity_type=entity_type,
                    filter_ids=filter_ids,
                    filter_field=filter_field,
                    fallback_mapping=fallback_mapping,
                    limit=limit,
                ):
                    yield doc

        source = _RecordingFilterableDataSource(documents=[SAMPLE_DOCUMENT_WITH_TERMS])
        wrapper = PublicationTermDataSource(data_source=source)

        async for _ in wrapper.fetch_filtered_with_fallback(
            entity_type="publication_term",
            filter_ids=["CHEMBL1123456"],
            filter_field="publication_id",
            fallback_mapping={"CHEMBL1123456": "Test"},
            limit=2,
        ):
            pass

        assert source.fallback_calls[-1]["entity_type"] == "publication"
        assert source.fallback_calls[-1]["limit"] == 100

    @pytest.mark.asyncio
    async def test_fetch_filtered_with_fallback_raises_for_non_filterable(self):
        """Test fetch_filtered_with_fallback raises TypeError."""
        source = MockDataSource()
        wrapper = PublicationTermDataSource(data_source=source)

        with pytest.raises(
            TypeError, match="does not implement FilterableDataSourcePort"
        ):
            async for _ in wrapper.fetch_filtered_with_fallback(
                entity_type="publication_term",
                filter_ids=["CHEMBL1"],
                filter_field="publication_id",
                fallback_mapping={},
            ):
                pass


@pytest.mark.unit
class TestPublicationTermGetSourceMetadata:
    """Tests for get_source_metadata delegation."""

    def test_get_source_metadata_delegates(self):
        """Test get_source_metadata delegates to wrapped adapter."""
        from unittest.mock import MagicMock

        source = MockDataSource()
        source.get_source_metadata = MagicMock(return_value="metadata")
        wrapper = PublicationTermDataSource(data_source=source)

        result = wrapper.get_source_metadata(api_version="v1")

        assert result == "metadata"
        source.get_source_metadata.assert_called_once_with("v1")

    def test_get_source_metadata_returns_none_when_not_supported(self):
        """Test get_source_metadata returns None if wrapped doesn't support it."""
        source = MockDataSource()
        wrapper = PublicationTermDataSource(data_source=source)

        result = wrapper.get_source_metadata()

        assert result is None
