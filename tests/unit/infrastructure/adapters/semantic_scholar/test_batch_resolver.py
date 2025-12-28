"""Tests for BatchResolver.

Tests cover:
- ID formatting with prefixes
- Chunking of large ID lists
- Batch resolution with different ID types
- Convenience methods for DOI, PMID, arXiv
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.semantic_scholar.batch import (
    MAX_BATCH_SIZE,
    BatchResolver,
    BatchResult,
    IdType,
    create_batch_resolver,
)
from bioetl.infrastructure.adapters.semantic_scholar.client import (
    SemanticScholarAdapter,
)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def rate_limiter() -> TokenBucket:
    """Create a rate limiter for testing."""
    return TokenBucket(rate=100.0, capacity=200, provider="semantic_scholar")


@pytest.fixture
def circuit_breaker() -> CircuitBreaker:
    """Create a circuit breaker for testing."""
    return CircuitBreaker(
        provider="semantic_scholar",
        failure_threshold=5,
        recovery_timeout=300,
    )


@pytest.fixture
def thread_pool() -> ThreadPoolExecutor:
    """Create a thread pool for testing."""
    pool = ThreadPoolExecutor(max_workers=2)
    yield pool
    pool.shutdown(wait=False)


@pytest.fixture
def adapter(
    mock_logger: MagicMock,
    rate_limiter: TokenBucket,
    circuit_breaker: CircuitBreaker,
    thread_pool: ThreadPoolExecutor,
) -> SemanticScholarAdapter:
    """Create a SemanticScholarAdapter for testing."""
    return SemanticScholarAdapter(
        logger=mock_logger,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        thread_pool=thread_pool,
    )


@pytest.fixture
def resolver(adapter: SemanticScholarAdapter) -> BatchResolver:
    """Create a BatchResolver for testing."""
    return BatchResolver(adapter=adapter)


class TestBatchResolverInitialization:
    """Tests for BatchResolver initialization."""

    def test_init_with_default_batch_size(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test initialization with default batch size."""
        resolver = BatchResolver(adapter=adapter)
        assert resolver.batch_size == MAX_BATCH_SIZE

    def test_init_with_custom_batch_size(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test initialization with custom batch size."""
        resolver = BatchResolver(adapter=adapter, batch_size=100)
        assert resolver.batch_size == 100

    def test_init_raises_for_batch_size_over_max(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that initialization raises for batch size over maximum."""
        with pytest.raises(ValueError, match="exceeds maximum"):
            BatchResolver(adapter=adapter, batch_size=501)

    def test_init_raises_for_zero_batch_size(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that initialization raises for zero batch size."""
        with pytest.raises(ValueError, match="must be positive"):
            BatchResolver(adapter=adapter, batch_size=0)

    def test_init_raises_for_negative_batch_size(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that initialization raises for negative batch size."""
        with pytest.raises(ValueError, match="must be positive"):
            BatchResolver(adapter=adapter, batch_size=-1)


class TestIdFormatting:
    """Tests for ID formatting."""

    def test_format_paper_id_no_prefix(self, resolver: BatchResolver) -> None:
        """Test that paper IDs are not prefixed."""
        formatted = resolver._format_id("abc123", IdType.PAPER_ID)
        assert formatted == "abc123"

    def test_format_doi_adds_prefix(self, resolver: BatchResolver) -> None:
        """Test that DOIs get DOI: prefix."""
        formatted = resolver._format_id("10.1038/nature12373", IdType.DOI)
        assert formatted == "DOI:10.1038/nature12373"

    def test_format_doi_no_double_prefix(self, resolver: BatchResolver) -> None:
        """Test that already-prefixed DOIs are not double-prefixed."""
        formatted = resolver._format_id("DOI:10.1038/nature12373", IdType.DOI)
        assert formatted == "DOI:10.1038/nature12373"

    def test_format_arxiv_adds_prefix(self, resolver: BatchResolver) -> None:
        """Test that arXiv IDs get ArXiv: prefix (as per S2 API)."""
        formatted = resolver._format_id("2103.15348", IdType.ARXIV)
        assert formatted == "ArXiv:2103.15348"

    def test_format_pmid_adds_prefix(self, resolver: BatchResolver) -> None:
        """Test that PMIDs get PubMed: prefix (as per S2 API)."""
        formatted = resolver._format_id("23831764", IdType.PMID)
        assert formatted == "PubMed:23831764"

    def test_format_mag_adds_prefix(self, resolver: BatchResolver) -> None:
        """Test that MAG IDs get MAG: prefix."""
        formatted = resolver._format_id("123456789", IdType.MAG)
        assert formatted == "MAG:123456789"

    def test_format_corpus_id_adds_prefix(self, resolver: BatchResolver) -> None:
        """Test that Corpus IDs get CorpusId: prefix."""
        formatted = resolver._format_id("12345", IdType.CORPUS_ID)
        assert formatted == "CorpusId:12345"


class TestIdChunking:
    """Tests for ID list chunking."""

    def test_chunk_empty_list(self, resolver: BatchResolver) -> None:
        """Test chunking of empty list."""
        chunks = resolver._chunk_ids([])
        assert chunks == []

    def test_chunk_single_item(self, resolver: BatchResolver) -> None:
        """Test chunking of single item."""
        chunks = resolver._chunk_ids(["id1"])
        assert chunks == [["id1"]]

    def test_chunk_under_batch_size(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test chunking of list under batch size."""
        resolver = BatchResolver(adapter=adapter, batch_size=10)
        chunks = resolver._chunk_ids(["id1", "id2", "id3"])
        assert chunks == [["id1", "id2", "id3"]]

    def test_chunk_exact_batch_size(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test chunking of list exactly matching batch size."""
        resolver = BatchResolver(adapter=adapter, batch_size=3)
        chunks = resolver._chunk_ids(["id1", "id2", "id3"])
        assert chunks == [["id1", "id2", "id3"]]

    def test_chunk_over_batch_size(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test chunking of list over batch size."""
        resolver = BatchResolver(adapter=adapter, batch_size=3)
        chunks = resolver._chunk_ids(["id1", "id2", "id3", "id4", "id5"])
        assert len(chunks) == 2
        assert chunks[0] == ["id1", "id2", "id3"]
        assert chunks[1] == ["id4", "id5"]


class TestResolve:
    """Tests for resolve method."""

    async def test_resolve_empty_list_returns_nothing(
        self, resolver: BatchResolver
    ) -> None:
        """Test that resolving empty list yields nothing."""
        results = [p async for p in resolver.resolve([])]
        assert results == []

    async def test_resolve_calls_adapter_fetch_by_ids(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that resolve calls adapter's _fetch_by_ids."""
        resolver = BatchResolver(adapter=adapter)

        mock_paper = {"semantic_scholar_id": "abc123", "title": "Test"}

        async def mock_fetch_by_ids(
            ids: list[str], id_type: str | None, limit: int | None = None
        ) -> Any:
            for paper in [mock_paper]:
                yield paper

        with patch.object(adapter, "_fetch_by_ids", mock_fetch_by_ids):
            results = [p async for p in resolver.resolve(["abc123"])]

        assert len(results) == 1
        assert results[0]["semantic_scholar_id"] == "abc123"

    async def test_resolve_formats_dois(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that resolve formats DOIs with prefix."""
        resolver = BatchResolver(adapter=adapter)
        captured_ids: list[str] = []

        async def mock_fetch_by_ids(
            ids: list[str], id_type: str | None, limit: int | None = None
        ) -> Any:
            captured_ids.extend(ids)
            return
            yield  # Make this a generator

        with patch.object(adapter, "_fetch_by_ids", mock_fetch_by_ids):
            _ = [
                p
                async for p in resolver.resolve(
                    ["10.1038/nature12373"], IdType.DOI
                )
            ]

        assert "DOI:10.1038/nature12373" in captured_ids


class TestResolveAll:
    """Tests for resolve_all method."""

    async def test_resolve_all_returns_batch_result(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that resolve_all returns BatchResult."""
        resolver = BatchResolver(adapter=adapter)

        mock_paper = {
            "semantic_scholar_id": "abc123",
            "doi": "10.1038/nature12373",
            "title": "Test",
        }

        async def mock_fetch_by_ids(
            ids: list[str], id_type: str | None, limit: int | None = None
        ) -> Any:
            yield mock_paper

        with patch.object(adapter, "_fetch_by_ids", mock_fetch_by_ids):
            result = await resolver.resolve_all(
                ["10.1038/nature12373", "not_found"],
                IdType.DOI,
            )

        assert isinstance(result, BatchResult)
        assert len(result.papers) == 1
        assert result.papers[0]["semantic_scholar_id"] == "abc123"
        # not_found should be in not_found list
        assert "not_found" in result.not_found


class TestConvenienceMethods:
    """Tests for convenience resolve methods."""

    async def test_resolve_dois(self, adapter: SemanticScholarAdapter) -> None:
        """Test resolve_dois convenience method."""
        resolver = BatchResolver(adapter=adapter)

        mock_paper = {"semantic_scholar_id": "abc123", "title": "Test"}

        async def mock_fetch_by_ids(
            ids: list[str], id_type: str | None, limit: int | None = None
        ) -> Any:
            yield mock_paper

        with patch.object(adapter, "_fetch_by_ids", mock_fetch_by_ids):
            results = [
                p async for p in resolver.resolve_dois(["10.1038/nature12373"])
            ]

        assert len(results) == 1

    async def test_resolve_pmids(self, adapter: SemanticScholarAdapter) -> None:
        """Test resolve_pmids convenience method."""
        resolver = BatchResolver(adapter=adapter)

        mock_paper = {"semantic_scholar_id": "abc123", "title": "Test"}

        async def mock_fetch_by_ids(
            ids: list[str], id_type: str | None, limit: int | None = None
        ) -> Any:
            yield mock_paper

        with patch.object(adapter, "_fetch_by_ids", mock_fetch_by_ids):
            # Test with int PMIDs
            results = [p async for p in resolver.resolve_pmids([23831764])]

        assert len(results) == 1

    async def test_resolve_arxiv(self, adapter: SemanticScholarAdapter) -> None:
        """Test resolve_arxiv convenience method."""
        resolver = BatchResolver(adapter=adapter)

        mock_paper = {"semantic_scholar_id": "abc123", "title": "Test"}

        async def mock_fetch_by_ids(
            ids: list[str], id_type: str | None, limit: int | None = None
        ) -> Any:
            yield mock_paper

        with patch.object(adapter, "_fetch_by_ids", mock_fetch_by_ids):
            results = [p async for p in resolver.resolve_arxiv(["2103.15348"])]

        assert len(results) == 1


class TestFactoryFunction:
    """Tests for create_batch_resolver factory."""

    def test_create_batch_resolver_default_size(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test factory with default batch size."""
        resolver = create_batch_resolver(adapter)
        assert resolver.batch_size == MAX_BATCH_SIZE
        assert resolver.adapter is adapter

    def test_create_batch_resolver_custom_size(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test factory with custom batch size."""
        resolver = create_batch_resolver(adapter, batch_size=100)
        assert resolver.batch_size == 100


class TestIdTypeEnum:
    """Tests for IdType enum."""

    def test_paper_id_value(self) -> None:
        """Test PAPER_ID enum value."""
        assert IdType.PAPER_ID.value == "paperId"

    def test_doi_value(self) -> None:
        """Test DOI enum value."""
        assert IdType.DOI.value == "DOI"

    def test_arxiv_value(self) -> None:
        """Test ARXIV enum value."""
        assert IdType.ARXIV.value == "ArXiv"

    def test_pmid_value(self) -> None:
        """Test PMID enum value."""
        assert IdType.PMID.value == "PubMed"
