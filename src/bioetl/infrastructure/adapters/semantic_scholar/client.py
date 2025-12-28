"""Semantic Scholar API client adapter.

Implements DataSourcePort for Semantic Scholar Graph API.

Requirements:
- Uses semanticscholar library (legacy sync)
- Rate limit: 100 req / 5 min (~0.33 req/sec) without key, 1 req/sec with key
- Health: lightweight paper query
- Entities: paper, author

API Reference: https://api.semanticscholar.org/api-docs/graph

Note:
    The semanticscholar library is synchronous, so all calls are wrapped
    via ThreadPoolExecutor using BaseSyncAdapter._run_in_executor().
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TYPE_CHECKING, Any

from semanticscholar import SemanticScholar
from semanticscholar.Paper import Paper

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket


# Default fields to request from S2 API (optimizes response size)
DEFAULT_PAPER_FIELDS: list[str] = [
    "paperId",
    "externalIds",
    "title",
    "authors",
    "venue",
    "year",
    "abstract",
    "citationCount",
    "influentialCitationCount",
    "fieldsOfStudy",
]

# Extended fields including embedding (for enrichment pipelines)
EXTENDED_PAPER_FIELDS: list[str] = [
    *DEFAULT_PAPER_FIELDS,
    "embedding",
]

# Lightweight field for health check
HEALTH_CHECK_FIELDS: list[str] = ["paperId", "title"]

# Known DOI for health probe (Nature paper with stable availability)
HEALTH_PROBE_DOI = "10.1038/nature12373"


class SemanticScholarAdapter(BaseSyncAdapter):
    """Semantic Scholar API adapter implementing DataSourcePort.

    Provides access to academic paper data with ML-enriched metadata
    including citation graphs, influence scores, and SPECTER embeddings.

    Uses semanticscholar library which is synchronous, so runs in ThreadPoolExecutor.

    All dependencies are injected via constructor (Composition Root pattern).

    Example:
        >>> # Dependencies created in Composition Root
        >>> rate_limiter = TokenBucket(rate=0.33, capacity=10)  # 100 req/5min
        >>> circuit_breaker = CircuitBreaker(provider="semantic_scholar")
        >>> thread_pool = ThreadPoolExecutor(max_workers=4)
        >>> adapter = SemanticScholarAdapter(
        ...     logger=logger,
        ...     rate_limiter=rate_limiter,
        ...     circuit_breaker=circuit_breaker,
        ...     thread_pool=thread_pool,
        ... )
        >>> papers = [p async for p in adapter.fetch("paper", query="transformer", limit=10)]
        >>> [p['paperId'] for p in papers]
        ['abc123', 'def456', ...]

    Attributes:
        provider_name: Unique identifier 'semantic_scholar'.
        api_key: Optional API key for higher rate limits.
        include_embedding: Whether to fetch SPECTER embeddings.
        fields: List of fields to request from API.

    """

    provider_name: str = "semantic_scholar"

    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
        api_key: str | None = None,
        include_embedding: bool = False,
        strict_error_handling: bool = False,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize Semantic Scholar client.

        All infrastructure components are injected from Composition Root.

        Args:
            logger: LoggerPort instance for structured logging.
            rate_limiter: Pre-configured token bucket rate limiter.
            circuit_breaker: Pre-configured circuit breaker.
            thread_pool: Pre-configured thread pool executor.
            api_key: Optional S2 API key for higher rate limits.
            include_embedding: Whether to include SPECTER embeddings.
            strict_error_handling: Whether to raise exceptions or log warnings.
            metrics: MetricsPort instance for metrics collection.

        """
        super().__init__(
            logger=logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            strict_error_handling=strict_error_handling,
            metrics=metrics,
        )

        self.api_key = api_key
        self.include_embedding = include_embedding
        self.fields = EXTENDED_PAPER_FIELDS if include_embedding else DEFAULT_PAPER_FIELDS

        # Lazy-initialized S2 client (created on first use)
        self._client: SemanticScholar | None = None

        self._fetch_strategies = {
            "paper": self._fetch_papers,
            "author": self._fetch_authors,
        }

    def _get_client(self) -> SemanticScholar:
        """Get or create SemanticScholar client instance.

        Lazy initialization allows for proper lifecycle management.

        Returns:
            Configured SemanticScholar client.

        """
        if self._client is None:
            self._client = SemanticScholar(api_key=self.api_key)
        return self._client

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from Semantic Scholar.

        Args:
            entity_type: Type of entity ('paper' or 'author').
            limit: Maximum number of records to fetch.
            query: Search query string.
            filter_ids: List of paper IDs, DOIs, or arXiv IDs for batch lookup.
            filter_field: Field type for filter_ids ('paperId', 'DOI', 'ArXiv').

        Yields:
            Dictionary records from Semantic Scholar API.

        Raises:
            ValueError: If entity_type is unsupported.

        """
        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        # If filter_ids provided, use batch lookup
        if filter_ids:
            async for record in self._fetch_by_ids(filter_ids, filter_field, limit):
                yield record
        else:
            # Standard query-based fetch
            async for record in strategy(query=query, limit=limit):
                yield record

    async def _fetch_papers(
        self,
        query: str | None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch papers by search query.

        Args:
            query: Search query string.
            limit: Maximum number of papers to return.

        Yields:
            Paper records as dictionaries.

        """
        if not query:
            raise ValueError("Query is required for paper search")

        await self.rate_limiter.acquire()

        client = self._get_client()

        # Search papers using S2 API
        # Use partial to bind keyword args since _run_in_executor only takes positional args
        search_func = partial(
            client.search_paper,
            query,
            limit=limit or 100,
            fields=self.fields,
        )
        papers = await self.circuit_breaker.call(
            self._run_in_executor,
            search_func,
        )

        for paper in papers or []:
            yield self._paper_to_dict(paper)

    async def _fetch_by_ids(
        self,
        paper_ids: list[str],
        id_type: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch papers by IDs using batch API.

        Supports paper IDs, DOIs (prefixed with DOI:), and arXiv IDs.

        Args:
            paper_ids: List of paper identifiers.
            id_type: Type of IDs ('paperId', 'DOI', 'ArXiv'). Auto-detected if None.
            limit: Maximum number of papers to return.

        Yields:
            Paper records as dictionaries.

        """
        # Prefix DOIs if id_type indicates DOI
        formatted_ids = []
        for pid in paper_ids:
            if id_type == "DOI" and not pid.startswith("DOI:"):
                formatted_ids.append(f"DOI:{pid}")
            elif id_type == "ArXiv" and not pid.startswith("ARXIV:"):
                formatted_ids.append(f"ARXIV:{pid}")
            else:
                formatted_ids.append(pid)

        await self.rate_limiter.acquire()

        client = self._get_client()

        # Use batch lookup (up to 500 IDs per request)
        # Use partial to bind keyword args since _run_in_executor only takes positional args
        get_func = partial(
            client.get_papers,
            formatted_ids,
            fields=self.fields,
        )
        papers = await self.circuit_breaker.call(
            self._run_in_executor,
            get_func,
        )

        fetched = 0
        for paper in papers or []:
            if paper is None:
                # Paper not found
                continue
            if limit and fetched >= limit:
                break
            yield self._paper_to_dict(paper)
            fetched += 1

    async def _fetch_authors(
        self,
        query: str | None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch authors by search query.

        Args:
            query: Author name search query.
            limit: Maximum number of authors to return.

        Yields:
            Author records as dictionaries.

        """
        if not query:
            raise ValueError("Query is required for author search")

        await self.rate_limiter.acquire()

        client = self._get_client()

        # Search authors using S2 API
        # Use partial to bind keyword args since _run_in_executor only takes positional args
        search_func = partial(
            client.search_author,
            query,
            limit=limit or 100,
        )
        authors = await self.circuit_breaker.call(
            self._run_in_executor,
            search_func,
        )

        for author in authors or []:
            yield self._author_to_dict(author)

    def _paper_to_dict(self, paper: Paper) -> dict[str, Any]:
        """Convert semanticscholar Paper to dictionary.

        Maps S2 API fields to Publication layer schema.

        Args:
            paper: SemanticScholar Paper object.

        Returns:
            Dictionary with paper data mapped to Publication schema.

        """
        # Extract external IDs
        external_ids = getattr(paper, "externalIds", {}) or {}

        # Extract DOI (lowercase for normalization)
        doi = external_ids.get("DOI")
        if doi:
            doi = doi.lower()

        # Extract PMID as int
        pmid = external_ids.get("PubMed")
        if pmid:
            try:
                pmid = int(pmid)
            except (ValueError, TypeError):
                pmid = None

        # Extract author names
        authors = []
        paper_authors = getattr(paper, "authors", []) or []
        for author in paper_authors:
            if hasattr(author, "name") and author.name:
                authors.append(author.name)

        # Extract embedding if present
        embedding: list[float] = []
        paper_embedding = getattr(paper, "embedding", None)
        if paper_embedding and hasattr(paper_embedding, "vector"):
            embedding = paper_embedding.vector or []

        # Extract fields of study
        fields_of_study = getattr(paper, "fieldsOfStudy", []) or []

        return {
            "semantic_scholar_id": paper.paperId,
            "doi": doi,
            "pmid": pmid,
            "title": getattr(paper, "title", None),
            "authors": authors,
            "journal": getattr(paper, "venue", None),
            "year": getattr(paper, "year", None),
            "abstract": getattr(paper, "abstract", None),
            "citation_count": getattr(paper, "citationCount", None),
            "influential_citation_count": getattr(paper, "influentialCitationCount", None),
            "fields_of_study": fields_of_study,
            "_embedding": embedding,
        }

    def _author_to_dict(self, author: Any) -> dict[str, Any]:
        """Convert semanticscholar Author to dictionary.

        Args:
            author: SemanticScholar Author object.

        Returns:
            Dictionary with author data.

        """
        return {
            "author_id": getattr(author, "authorId", None),
            "name": getattr(author, "name", None),
            "affiliations": getattr(author, "affiliations", []) or [],
            "paper_count": getattr(author, "paperCount", None),
            "citation_count": getattr(author, "citationCount", None),
            "h_index": getattr(author, "hIndex", None),
        }

    async def _probe_health(self) -> HealthStatus:
        """Perform Semantic Scholar-specific health probe.

        Overrides BaseSyncAdapter._probe_health() to use lightweight
        paper query for health assessment.

        Returns:
            HealthStatus based on probe response:
            - HEALTHY: API responds successfully
            - DEGRADED: Empty response or partial failure
            - UNHEALTHY: Circuit breaker is open

        Raises:
            Exception: On request failure (base class handles via _fallback_health_status).

        """
        try:
            await self.rate_limiter.acquire()

            client = self._get_client()

            # Lightweight query: fetch known paper by DOI
            # Use partial to bind keyword args since _run_in_executor only takes positional args
            get_func = partial(
                client.get_paper,
                f"DOI:{HEALTH_PROBE_DOI}",
                fields=HEALTH_CHECK_FIELDS,
            )
            paper = await self.circuit_breaker.call(
                self._run_in_executor,
                get_func,
            )

            if paper and paper.paperId:
                return self._fallback_health_status()

            self.logger.warning(
                "health_check_degraded",
                provider=self.provider_name,
                reason="empty_response",
            )
            return HealthStatus.DEGRADED

        except CircuitBreakerOpenError:
            self.logger.warning(
                "health_check_circuit_open",
                provider=self.provider_name,
            )
            return HealthStatus.UNHEALTHY

        except Exception as e:
            error_classifier = ErrorClassifier()
            error_type = error_classifier.classify(e)
            self.logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error_type=error_type.value,
                error=str(e),
            )
            raise  # Let base class handle via _fallback_health_status()

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"SemanticScholarAdapter("
            f"rate={self.rate_limiter.rate}, "
            f"api_key={'set' if self.api_key else 'none'}, "
            f"embedding={self.include_embedding})"
        )
