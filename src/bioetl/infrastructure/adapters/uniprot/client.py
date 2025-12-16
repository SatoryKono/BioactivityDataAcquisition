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
from typing import Any

import httpx

from bioetl.infrastructure.config import get_settings
from bioetl.domain.types import HealthStatus, Watermark
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

logger = logging.getLogger(__name__)


class UniProtClient(PaginatedFetcherMixin):
    """UniProt API client implementing DataSourcePort.

    Provides access to protein sequence and functional information from UniProt database.
    Uses UnifiedHTTPClient for resilient API access and PaginatedFetcherMixin for
    cursor-based pagination.
    """

    def __init__(
        self,
        http_client: UnifiedHTTPClient | None = None,
        api_key: str | None = None,
        base_url: str = "https://rest.uniprot.org",
        rate: float | None = None,  # Optional override
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 300,
    ) -> None:
        """Initialize UniProt client.

        Args:
            http_client: Pre-configured UnifiedHTTPClient (preferred)
            api_key: UniProt API key
            base_url: UniProt REST API base URL
            rate: Rate limit override
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout: Recovery timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.provider_name = "uniprot"

        if http_client:
            self.http_client = http_client
            # Note: We assume http_client is already configured with correct rate limit
        else:
            # Legacy initialization (for backward compatibility or standalone use)
            if rate is None:
                rate = 100.0 if api_key else 10.0

            rate_limiter = TokenBucket(rate=rate, capacity=int(rate * 2))
            circuit_breaker = CircuitBreaker(
                provider=self.provider_name,
                failure_threshold=circuit_breaker_threshold,
                recovery_timeout=circuit_breaker_timeout,
            )
            self.http_client = UnifiedHTTPClient(
                rate_limiter=rate_limiter, circuit_breaker=circuit_breaker
            )

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

    async def _fetch_proteins(
        self,
        query: str | None,
        watermark: Watermark | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein entries using paginated mixin."""
        query = self._build_query(query, watermark)
        size = 500
        url = f"{self.base_url}/uniprotkb/search"

        initial_params = {
            "query": query,
            "size": size,
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

        def extract_items(response: httpx.Response) -> list[dict[str, Any]]:
            if response.status_code != 200:
                return []
            data = response.json()
            return data.get("results", [])

        def next_page_params(
            response: httpx.Response, current_params: dict[str, Any]
        ) -> dict[str, Any] | None:
            if response.status_code != 200:
                return None
            data = response.json()
            cursor = data.get("nextCursor")
            if not cursor:
                return None
            # Update params with new cursor
            new_params = current_params.copy()
            new_params["cursor"] = cursor
            return new_params

        async for item in self.fetch_paginated(
            url=url,
            initial_params=initial_params,
            extract_items=extract_items,
            next_page_params=next_page_params,
            limit=limit,
        ):
            yield item

    def _build_query(self, query: str | None, watermark: Watermark | None) -> str:
        """Build the query string."""
        query = query or "*"
        if watermark:
            query = f"{query} AND accession_id:[{watermark} TO *]"
        return query

    async def _fetch_features(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein features from UniProt."""
        if not query:
            raise ValueError("Query is required for feature search")

        fetched = 0
        try:
            url = f"{self.base_url}/uniprotkb/{query}.json"
            response = await self.http_client.get(url)

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
            if get_settings().strict_error_handling:
                raise
            return

    async def _fetch_sequences(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein sequences from UniProt."""
        if not query:
            raise ValueError("Query is required for sequence fetch")

        fetched = 0
        try:
            url = f"{self.base_url}/uniprotkb/stream"
            response = await self.http_client.get(
                url, params={"query": query, "format": "fasta"}
            )

            if response.status_code == 200:
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
            if get_settings().strict_error_handling:
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
        """Check UniProt API health status."""
        health_url = f"{self.base_url}/rest/beta/health"

        try:
            response = await self.http_client.get(health_url)

            if response.status_code == 200:
                # Check circuit breaker from http_client
                cb = self.http_client.circuit_breaker
                cb_state = cb.get_state()
                failure_count = cb.get_failure_count()

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
        if hasattr(self.http_client, "__aexit__"):
            # If we own it or if it supports close
            pass
        # UnifiedHTTPClient manages its own lifecycle via context manager usually,
        # but here we might not be in one if injected.

    def __repr__(self) -> str:
        """String representation."""
        has_key = "with API key" if self.api_key else "without API key"
        return f"UniProtClient(base_url='{self.base_url}', {has_key})"
