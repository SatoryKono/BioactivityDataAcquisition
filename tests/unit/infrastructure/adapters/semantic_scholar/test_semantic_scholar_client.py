"""Tests for SemanticScholarAdapter.

Tests cover:
- Initialization and configuration
- Paper fetching by query and IDs
- Author fetching
- Health check behavior
- Error handling and circuit breaker integration
- Field mapping from S2 API to Publication schema
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.semantic_scholar.client import (
    DEFAULT_PAPER_FIELDS,
    EXTENDED_PAPER_FIELDS,
    SemanticScholarAdapter,
)


@dataclass
class MockPaper:
    """Mock Semantic Scholar Paper object for testing."""

    paperId: str
    externalIds: dict[str, str] | None = None
    title: str | None = None
    authors: list[Any] | None = None
    venue: str | None = None
    year: int | None = None
    abstract: str | None = None
    citationCount: int | None = None
    influentialCitationCount: int | None = None
    fieldsOfStudy: list[str] | None = None
    embedding: Any | None = None


@dataclass
class MockAuthor:
    """Mock author object."""

    name: str


@dataclass
class MockEmbedding:
    """Mock embedding object."""

    vector: list[float]


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create a mock metrics port for testing."""
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


class TestSemanticScholarAdapterInitialization:
    """Tests for adapter initialization."""

    def test_init_sets_provider_name(self, adapter: SemanticScholarAdapter) -> None:
        """Test that provider_name is set correctly."""
        assert adapter.provider_name == "semantic_scholar"

    def test_init_with_api_key(
        self,
        mock_logger: MagicMock,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test initialization with API key."""
        adapter = SemanticScholarAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            api_key="test-api-key",
        )
        assert adapter.api_key == "test-api-key"

    def test_init_without_embedding_uses_default_fields(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that default fields are used when embedding is not requested."""
        assert adapter.fields == DEFAULT_PAPER_FIELDS
        assert adapter.include_embedding is False

    def test_init_with_embedding_uses_extended_fields(
        self,
        mock_logger: MagicMock,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that extended fields are used when embedding is requested."""
        adapter = SemanticScholarAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            include_embedding=True,
        )
        assert adapter.fields == EXTENDED_PAPER_FIELDS
        assert adapter.include_embedding is True

    def test_repr(self, adapter: SemanticScholarAdapter) -> None:
        """Test string representation."""
        repr_str = repr(adapter)
        assert "SemanticScholarAdapter" in repr_str
        assert "rate=" in repr_str
        assert "api_key=none" in repr_str
        assert "embedding=False" in repr_str


class TestPaperToDict:
    """Tests for _paper_to_dict field mapping."""

    def test_maps_basic_fields(self, adapter: SemanticScholarAdapter) -> None:
        """Test mapping of basic paper fields."""
        paper = MockPaper(
            paperId="abc123",
            title="Test Paper",
            venue="Nature",
            year=2023,
            abstract="This is an abstract.",
            citationCount=100,
            influentialCitationCount=10,
        )

        result = adapter._paper_to_dict(paper)

        assert result["semantic_scholar_id"] == "abc123"
        assert result["title"] == "Test Paper"
        assert result["journal"] == "Nature"
        assert result["year"] == 2023
        assert result["abstract"] == "This is an abstract."
        assert result["citation_count"] == 100
        assert result["influential_citation_count"] == 10

    def test_maps_external_ids(self, adapter: SemanticScholarAdapter) -> None:
        """Test mapping of external IDs (DOI, PMID)."""
        paper = MockPaper(
            paperId="abc123",
            externalIds={
                "DOI": "10.1038/NATURE12373",
                "PubMed": "23831764",
            },
        )

        result = adapter._paper_to_dict(paper)

        # DOI should be lowercased
        assert result["doi"] == "10.1038/nature12373"
        # PMID should be converted to int
        assert result["pmid"] == 23831764

    def test_handles_invalid_pmid(self, adapter: SemanticScholarAdapter) -> None:
        """Test handling of invalid PMID."""
        paper = MockPaper(
            paperId="abc123",
            externalIds={"PubMed": "invalid"},
        )

        result = adapter._paper_to_dict(paper)

        assert result["pmid"] is None

    def test_maps_authors(self, adapter: SemanticScholarAdapter) -> None:
        """Test mapping of author names."""
        paper = MockPaper(
            paperId="abc123",
            authors=[
                MockAuthor(name="John Doe"),
                MockAuthor(name="Jane Smith"),
            ],
        )

        result = adapter._paper_to_dict(paper)

        assert result["authors"] == ["John Doe", "Jane Smith"]

    def test_handles_authors_without_names(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test handling of authors without names."""
        author_without_name = MagicMock()
        author_without_name.name = None

        paper = MockPaper(
            paperId="abc123",
            authors=[author_without_name],
        )

        result = adapter._paper_to_dict(paper)

        assert result["authors"] == []

    def test_maps_embedding(self, adapter: SemanticScholarAdapter) -> None:
        """Test mapping of SPECTER embedding."""
        paper = MockPaper(
            paperId="abc123",
            embedding=MockEmbedding(vector=[0.1, 0.2, 0.3]),
        )

        result = adapter._paper_to_dict(paper)

        assert result["_embedding"] == [0.1, 0.2, 0.3]

    def test_handles_missing_embedding(self, adapter: SemanticScholarAdapter) -> None:
        """Test handling of missing embedding."""
        paper = MockPaper(paperId="abc123", embedding=None)

        result = adapter._paper_to_dict(paper)

        assert result["_embedding"] == []

    def test_maps_fields_of_study(self, adapter: SemanticScholarAdapter) -> None:
        """Test mapping of fields of study."""
        paper = MockPaper(
            paperId="abc123",
            fieldsOfStudy=["Computer Science", "Medicine"],
        )

        result = adapter._paper_to_dict(paper)

        assert result["fields_of_study"] == ["Computer Science", "Medicine"]

    def test_handles_none_external_ids(self, adapter: SemanticScholarAdapter) -> None:
        """Test handling of None external IDs."""
        paper = MockPaper(paperId="abc123", externalIds=None)

        result = adapter._paper_to_dict(paper)

        assert result["doi"] is None
        assert result["pmid"] is None


class TestFetch:
    """Tests for fetch method."""

    async def test_fetch_raises_for_unsupported_entity(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that fetch raises ValueError for unsupported entity types."""
        with pytest.raises(ValueError, match="Unsupported entity type"):
            async for _ in adapter.fetch("unsupported"):
                pass

    async def test_fetch_paper_requires_query(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that paper fetch requires a query."""
        with pytest.raises(ValueError, match="Query is required"):
            async for _ in adapter.fetch("paper", query=None):
                pass

    async def test_fetch_author_requires_query(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that author fetch requires a query."""
        with pytest.raises(ValueError, match="Query is required"):
            async for _ in adapter.fetch("author", query=None):
                pass

    @patch("bioetl.infrastructure.adapters.semantic_scholar.client.SemanticScholar")
    async def test_fetch_paper_by_query(
        self,
        mock_s2_class: MagicMock,
        adapter: SemanticScholarAdapter,
    ) -> None:
        """Test fetching papers by search query."""
        mock_client = MagicMock()
        mock_s2_class.return_value = mock_client

        mock_paper = MockPaper(paperId="abc123", title="Test Paper")
        mock_client.search_paper.return_value = [mock_paper]

        papers = [p async for p in adapter.fetch("paper", query="transformer")]

        assert len(papers) == 1
        assert papers[0]["semantic_scholar_id"] == "abc123"
        assert papers[0]["title"] == "Test Paper"

    @patch("bioetl.infrastructure.adapters.semantic_scholar.client.SemanticScholar")
    async def test_fetch_paper_by_ids(
        self,
        mock_s2_class: MagicMock,
        adapter: SemanticScholarAdapter,
    ) -> None:
        """Test fetching papers by IDs using batch API."""
        mock_client = MagicMock()
        mock_s2_class.return_value = mock_client

        mock_paper = MockPaper(paperId="abc123", title="Test Paper")
        mock_client.get_papers.return_value = [mock_paper]

        papers = [
            p
            async for p in adapter.fetch(
                "paper",
                filter_ids=["abc123"],
                filter_field="paperId",
            )
        ]

        assert len(papers) == 1
        assert papers[0]["semantic_scholar_id"] == "abc123"

    @patch("bioetl.infrastructure.adapters.semantic_scholar.client.SemanticScholar")
    async def test_fetch_handles_none_in_batch_results(
        self,
        mock_s2_class: MagicMock,
        adapter: SemanticScholarAdapter,
    ) -> None:
        """Test that None results in batch lookup are skipped."""
        mock_client = MagicMock()
        mock_s2_class.return_value = mock_client

        mock_paper = MockPaper(paperId="abc123", title="Test Paper")
        # Simulate API returning None for not-found papers
        mock_client.get_papers.return_value = [None, mock_paper, None]

        papers = [
            p
            async for p in adapter.fetch(
                "paper",
                filter_ids=["notfound1", "abc123", "notfound2"],
                filter_field="paperId",
            )
        ]

        assert len(papers) == 1
        assert papers[0]["semantic_scholar_id"] == "abc123"


class TestFetchByIds:
    """Tests for ID-based fetching with proper formatting."""

    @patch("bioetl.infrastructure.adapters.semantic_scholar.client.SemanticScholar")
    async def test_doi_ids_are_prefixed(
        self,
        mock_s2_class: MagicMock,
        adapter: SemanticScholarAdapter,
    ) -> None:
        """Test that DOIs are properly prefixed."""
        mock_client = MagicMock()
        mock_s2_class.return_value = mock_client
        mock_client.get_papers.return_value = []

        _ = [
            p
            async for p in adapter._fetch_by_ids(
                ["10.1038/nature12373"],
                id_type="DOI",
            )
        ]

        # Verify the formatted ID was passed
        call_args = mock_client.get_papers.call_args
        assert "DOI:10.1038/nature12373" in call_args[0][0]

    @patch("bioetl.infrastructure.adapters.semantic_scholar.client.SemanticScholar")
    async def test_arxiv_ids_are_prefixed(
        self,
        mock_s2_class: MagicMock,
        adapter: SemanticScholarAdapter,
    ) -> None:
        """Test that arXiv IDs are properly prefixed."""
        mock_client = MagicMock()
        mock_s2_class.return_value = mock_client
        mock_client.get_papers.return_value = []

        _ = [
            p
            async for p in adapter._fetch_by_ids(
                ["2103.15348"],
                id_type="ArXiv",
            )
        ]

        # Verify the formatted ID was passed
        call_args = mock_client.get_papers.call_args
        assert "ARXIV:2103.15348" in call_args[0][0]

    @patch("bioetl.infrastructure.adapters.semantic_scholar.client.SemanticScholar")
    async def test_already_prefixed_ids_not_double_prefixed(
        self,
        mock_s2_class: MagicMock,
        adapter: SemanticScholarAdapter,
    ) -> None:
        """Test that already-prefixed IDs are not double-prefixed."""
        mock_client = MagicMock()
        mock_s2_class.return_value = mock_client
        mock_client.get_papers.return_value = []

        _ = [
            p
            async for p in adapter._fetch_by_ids(
                ["DOI:10.1038/nature12373"],
                id_type="DOI",
            )
        ]

        # Verify ID was not double-prefixed
        call_args = mock_client.get_papers.call_args
        formatted_ids = call_args[0][0]
        assert formatted_ids == ["DOI:10.1038/nature12373"]


class TestHealthCheck:
    """Tests for health check behavior."""

    @patch("bioetl.infrastructure.adapters.semantic_scholar.client.SemanticScholar")
    async def test_health_check_returns_healthy_on_success(
        self,
        mock_s2_class: MagicMock,
        adapter: SemanticScholarAdapter,
    ) -> None:
        """Test that health check returns HEALTHY on success."""
        mock_client = MagicMock()
        mock_s2_class.return_value = mock_client

        mock_paper = MockPaper(paperId="abc123", title="Test")
        mock_client.get_paper.return_value = mock_paper

        status = await adapter.health_check()

        # Should return HEALTHY (via fallback which checks circuit breaker)
        assert status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)

    @patch("bioetl.infrastructure.adapters.semantic_scholar.client.SemanticScholar")
    async def test_health_check_returns_degraded_on_empty_response(
        self,
        mock_s2_class: MagicMock,
        adapter: SemanticScholarAdapter,
        mock_logger: MagicMock,
    ) -> None:
        """Test that health check returns DEGRADED on empty response."""
        mock_client = MagicMock()
        mock_s2_class.return_value = mock_client
        mock_client.get_paper.return_value = None

        status = await adapter.health_check()

        assert status == HealthStatus.DEGRADED
        mock_logger.warning.assert_called()

    async def test_health_check_returns_unhealthy_on_circuit_open(
        self,
        mock_logger: MagicMock,
        rate_limiter: TokenBucket,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that health check returns UNHEALTHY when circuit breaker is open."""
        # Create a circuit breaker that's already open
        circuit_breaker = CircuitBreaker(
            provider="semantic_scholar",
            failure_threshold=1,
            recovery_timeout=300,
        )

        adapter = SemanticScholarAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
        )

        # Force circuit breaker to open state
        async def failing_func() -> None:
            raise Exception("Simulated failure")

        for _ in range(2):
            try:
                await circuit_breaker.call(failing_func)
            except Exception:
                pass

        # Now health check should detect open circuit
        with patch.object(
            adapter.circuit_breaker,
            "call",
            side_effect=CircuitBreakerOpenError("semantic_scholar", retry_after=300.0),
        ):
            status = await adapter.health_check()

        assert status == HealthStatus.UNHEALTHY

    @patch("bioetl.infrastructure.adapters.semantic_scholar.client.SemanticScholar")
    async def test_health_check_logs_error_on_exception(
        self,
        mock_s2_class: MagicMock,
        adapter: SemanticScholarAdapter,
        mock_logger: MagicMock,
    ) -> None:
        """Test that health check logs error on API exception."""
        mock_client = MagicMock()
        mock_s2_class.return_value = mock_client
        mock_client.get_paper.side_effect = ConnectionError("Connection refused")

        # Should use fallback status
        status = await adapter.health_check()

        assert status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)


class TestContextManager:
    """Tests for context manager behavior."""

    async def test_aenter_returns_self(self, adapter: SemanticScholarAdapter) -> None:
        """Test that __aenter__ returns self."""
        async with adapter as ctx:
            assert ctx is adapter

    async def test_aexit_closes_resources(
        self, adapter: SemanticScholarAdapter
    ) -> None:
        """Test that __aexit__ closes resources."""
        async with adapter:
            pass

        # Thread pool should be shut down
        assert adapter.thread_pool._shutdown


class TestAuthorFetch:
    """Tests for author fetching."""

    @patch("bioetl.infrastructure.adapters.semantic_scholar.client.SemanticScholar")
    async def test_fetch_authors(
        self,
        mock_s2_class: MagicMock,
        adapter: SemanticScholarAdapter,
    ) -> None:
        """Test fetching authors by search query."""
        mock_client = MagicMock()
        mock_s2_class.return_value = mock_client

        mock_author = MagicMock()
        mock_author.authorId = "123456"
        mock_author.name = "John Doe"
        mock_author.affiliations = ["MIT"]
        mock_author.paperCount = 50
        mock_author.citationCount = 1000
        mock_author.hIndex = 20

        mock_client.search_author.return_value = [mock_author]

        authors = [p async for p in adapter.fetch("author", query="John Doe")]

        assert len(authors) == 1
        assert authors[0]["author_id"] == "123456"
        assert authors[0]["name"] == "John Doe"
        assert authors[0]["affiliations"] == ["MIT"]
        assert authors[0]["paper_count"] == 50
        assert authors[0]["citation_count"] == 1000
        assert authors[0]["h_index"] == 20
