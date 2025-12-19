"""UniProt API client adapter.

Implements RULES.md Appendix A - UniProt specifications.

Requirements:
- Uses httpx for async REST API access
- Rate limit: 100 req/sec (with API key)
- Health check: GET /rest/beta/health
- Entities: proteins, features, sequences

Documentation: https://www.uniprot.org/help/api
"""

import logging
from collections.abc import AsyncIterator
from typing import Any, Self

import httpx

from bioetl.domain.types import HealthStatus, Watermark
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin

logger = logging.getLogger(__name__)


class UniProtClient(PaginatedFetcherMixin):
    """UniProt API client implementing DataSourcePort.

    Provides access to protein sequence and functional information from UniProt database.

    Example:
        >>> client = UniProtClient(api_key="your_api_key")
        >>> # Search proteins by gene name
        >>> async for protein in client.fetch("protein", query="gene:TP53", limit=10):
        ...     print(f"Protein: {protein['primaryAccession']}")
        >>> # Check health
        >>> status = await client.health_check()
        >>> print(f"UniProt is {status}")
    """

    provider_name: str = "uniprot"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://rest.uniprot.org",
        rate: float = 100.0,  # 100 req/sec with API key
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 300,
        strict_error_handling: bool = False,
    ) -> None:
        """Initialize UniProt client.

        Args:
            api_key: UniProt API key (optional, increases rate limit)
            base_url: UniProt REST API base URL
            rate: Requests per second (default: 100.0 with API key, 10.0 without)
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout: Recovery timeout in seconds
            strict_error_handling: Whether to raise exceptions (True) or log warnings (False)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.provider_name = "uniprot"
        self.strict_error_handling = strict_error_handling

        # Adjust rate if no API key
        if not api_key:
            rate = 10.0  # Lower rate limit without API key

        # Rate limiter
        self.rate_limiter = TokenBucket(rate=rate, capacity=int(rate * 2))

        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            provider=self.provider_name,
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_breaker_timeout,
        )

        # HTTP client
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        self.http_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0,
        )

    async def __aenter__(self) -> Self:
        """Enter async context manager.

        Initializes HTTP client if not already active.
        """
        if self.http_client.is_closed:
             # Re-initialize if closed
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self.http_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0,
            )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager.

        Closes HTTP client.
        """
        await self.http_client.aclose()

    async def fetch(
        self,
        entity_type: str,
        query: str | None = None,
        watermark: Watermark | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from UniProt.

        Implements DataSourcePort.fetch() interface.

        Args:
            entity_type: Type of entity ('protein', 'feature', 'sequence')
            query: Search query (gene name, organism, keyword, etc.)
            watermark: Last accession for incremental load
            limit: Maximum number of records

        Yields:
            Raw records as dictionaries

        Raises:
            ValueError: If entity_type is not supported
            CircuitBreakerOpenError: If circuit breaker is open

        Example:
            >>> client = UniProtClient()
            >>> # Search by gene name and organism
            >>> async for protein in client.fetch(
            ...     "protein",
            ...     query="gene:BRCA1 AND organism_id:9606",
            ...     limit=5
            ... ):
            ...     print(f"Accession: {protein['primaryAccession']}")
        """
        # Apply rate limiting
        await self.rate_limiter.acquire()

        if entity_type == "protein":
            async for record in self._fetch_proteins(query, watermark, limit):
                yield record
        elif entity_type == "feature":
            async for record in self._fetch_features(query, limit):
                yield record
        elif entity_type == "sequence":
            async for record in self._fetch_sequences(query, limit):
                yield record
        else:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: protein, feature, sequence"
            )

    def _build_protein_fetch_params(
        self, query: str, size: int, fetched: int, limit: int | None, cursor: str | None
    ) -> dict[str, Any]:
        """Build the parameter dictionary for a protein fetch request."""
        params = {
            "query": query,
            "size": min(size, (limit - fetched) if limit else size),
            "format": "json",
            "fields": ",".join(
                [
                    "accession",
                    "id",
                    "gene_names",
                    "organism_name",
                    "organism_id",
                    "protein_name",
                    "length",
                    "sequence",
                    "cc_function",
                    "ft_domain",
                    "xref_pdb",
                    "xref_chembl",
                ]
            ),
        }
        if cursor:
            params["cursor"] = cursor
        return params

    async def _process_protein_response(
        self, response: httpx.Response
    ) -> tuple[list, str | None]:
        """Processes the HTTP response from a protein fetch request."""
        if response.status_code != 200:
            return [], None
        data = response.json()
        results = data.get("results", [])
        cursor = data.get("nextCursor")
        return results, cursor

    def _build_query(self, query: str | None, watermark: Watermark | None) -> str:
        """Build the query string."""
        query = query or "*"
        if watermark:
            query = f"{query} AND accession_id:[{watermark.to_api_param()} TO *]"
        return query

    async def _fetch_proteins(
        self,
        query: str | None,
        watermark: Watermark | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein entries from UniProt."""
        query = self._build_query(query, watermark)
        size = 500

        async def fetch_page(
            cursor: str | None, fetched: int
        ) -> tuple[list[dict[str, Any]], str | None]:
            """Callback for pagination."""
            await self.rate_limiter.acquire()
            params = self._build_protein_fetch_params(
                query, size, fetched, limit, cursor
            )
            try:
                response = await self.circuit_breaker.call(
                    self.http_client.get, "/uniprotkb/search", params=params
                )
                return await self._process_protein_response(response)
            except Exception:
                logger.error(
                    "UniProt protein fetch failed",
                    exc_info=True,
                    extra={"query": query, "cursor": cursor},
                )
                if self.strict_error_handling:
                    raise
                return [], None

        async for item in self.paginated_fetch(fetch_page, limit=limit):
            yield item

    async def _fetch_features(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein features from UniProt.

        Args:
            query: Protein accession or search query
            limit: Max records

        Yields:
            Feature records
        """
        if not query:
            raise ValueError("Query is required for feature search")

        fetched = 0

        # Get protein first
        await self.rate_limiter.acquire()

        try:
            response = await self.circuit_breaker.call(
                self.http_client.get,
                f"/uniprotkb/{query}.json",
            )

            if response.status_code == 200:
                protein = response.json()
                features = protein.get("features", [])

                for feature in features:
                    if limit and fetched >= limit:
                        break

                    yield {
                        "accession": query,
                        "type": feature.get("type"),
                        "location": feature.get("location"),
                        "description": feature.get("description"),
                    }
                    fetched += 1

        except Exception:
            logger.warning(
                "UniProt feature fetch failed",
                exc_info=True,
                extra={"accession": query},
            )
            if self.strict_error_handling:
                raise
            return

    async def _fetch_sequences(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein sequences from UniProt.

        Args:
            query: Protein accession or search query
            limit: Max records

        Yields:
            Sequence records
        """
        if not query:
            raise ValueError("Query is required for sequence fetch")

        fetched = 0

        # Fetch in FASTA format
        await self.rate_limiter.acquire()

        try:
            response = await self.circuit_breaker.call(
                self.http_client.get,
                "/uniprotkb/stream",
                params={
                    "query": query,
                    "format": "fasta",
                },
            )

            if response.status_code == 200:
                # Parse FASTA format
                fasta_text = response.text
                sequences = self._parse_fasta(fasta_text)

                for seq_record in sequences:
                    if limit and fetched >= limit:
                        break

                    yield seq_record
                    fetched += 1

        except Exception:
            logger.warning(
                "UniProt sequence fetch failed",
                exc_info=True,
                extra={"query": query},
            )
            if self.strict_error_handling:
                raise
            return

    def _parse_fasta(self, fasta_text: str) -> list[dict[str, Any]]:
        """Parse FASTA format text.

        Args:
            fasta_text: FASTA formatted text

        Returns:
            List of sequence records
        """
        records = []
        current_header = None
        current_sequence = []

        for line in fasta_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            if line.startswith(">"):
                # New sequence
                if current_header:
                    records.append(
                        {
                            "header": current_header,
                            "sequence": "".join(current_sequence),
                        }
                    )

                current_header = line[1:]  # Remove '>'
                current_sequence = []
            else:
                current_sequence.append(line)

        # Add last sequence
        if current_header:
            records.append(
                {
                    "header": current_header,
                    "sequence": "".join(current_sequence),
                }
            )

        return records

    async def health_check(self) -> HealthStatus:
        """Check UniProt API health status.

        Implements DataSourcePort.health_check() interface.

        Uses dedicated health endpoint: GET /rest/beta/health

        Returns:
            HealthStatus enum value

        Example:
            >>> client = UniProtClient()
            >>> status = await client.health_check()
            >>> print(f"UniProt is {status.value}")
        """
        health_url = "/rest/beta/health"

        try:
            response = await self.http_client.get(health_url)

            if response.status_code == 200:
                # Check circuit breaker state
                cb_state = self.circuit_breaker.get_state()
                failure_count = self.circuit_breaker.get_failure_count()

                if cb_state.value == "CLOSED" and failure_count == 0:
                    return HealthStatus.HEALTHY
                elif failure_count <= 2:
                    return HealthStatus.DEGRADED
                else:
                    return HealthStatus.UNHEALTHY
            else:
                return HealthStatus.DEGRADED

        except Exception:
            return HealthStatus.UNHEALTHY

    async def close(self) -> None:
        """Close HTTP client connections."""
        await self.http_client.aclose()

    async def aclose(self) -> None:
        """Gracefully close resources.

        Implements DataSourcePort.aclose().
        """
        await self.close()

    def __repr__(self) -> str:
        """String representation."""
        has_key = "with API key" if self.api_key else "without API key"
        return f"UniProtClient(base_url='{self.base_url}', {has_key})"
