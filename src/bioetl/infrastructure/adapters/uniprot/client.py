"""UniProt API client adapter.

Implements RULES.md Appendix A - UniProt specifications.

Requirements:
- Uses httpx for async REST API access
- Rate limit: 100 req/sec (with API key)
- Health check: Search probe (Ubiquitin)
- Entities: proteins, features, sequences

Documentation: https://www.uniprot.org/help/api
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from bioetl.domain.types import HealthStatus, Watermark
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin
from bioetl.infrastructure.adapters.logging_utils import log_adapter_error

logger = logging.getLogger(__name__)


class UniProtClient(BaseHttpAdapter, PaginatedFetcherMixin):
    """UniProt API client implementing DataSourcePort.

    Provides access to protein sequence and functional information from UniProt database.
    """

    provider_name: str = "uniprot"

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        api_key: str | None = None,
        base_url: str = "https://rest.uniprot.org",
        strict_error_handling: bool = False,
    ) -> None:
        """Initialize UniProt client.

        Args:
            http_client: Injected UnifiedHTTPClient
            api_key: UniProt API key (optional)
            base_url: UniProt REST API base URL
            strict_error_handling: Whether to raise exceptions (True) or log warnings (False)
        """
        super().__init__(http_client)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.strict_error_handling = strict_error_handling
        self._fetch_strategies = {
            "protein": self._fetch_proteins,
            "feature": self._fetch_features,
            "sequence": self._fetch_sequences,
        }

    async def fetch(
        self,
        entity_type: str,
        watermark: Watermark | None = None,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: set[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from UniProt."""
        # Note: filter_ids and filter_field are ignored for UniProt -
        # filtering should be done via query parameter
        _ = filter_ids, filter_field  # Mark as intentionally unused
        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        # Ensure arguments are passed correctly to strategies
        async for record in strategy(query=query, watermark=watermark, limit=limit):
            yield record

    def _build_protein_fetch_params(
        self, query: str, size: int, fetched: int, limit: int | None, cursor: str | None
    ) -> dict[str, Any]:
        """Build the parameter dictionary for a protein fetch request."""
        fields = [
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
        params = {
            "query": query,
            "size": min(size, (limit - fetched) if limit else size),
            "format": "json",
            "fields": ",".join(fields),
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
            params = self._build_protein_fetch_params(
                query, size, fetched, limit, cursor
            )
            try:
                response = await self.http_client.get(
                    f"{self.base_url}/uniprotkb/search", params=params
                )
                return await self._process_protein_response(response)
            except Exception:
                self._handle_fetch_error("protein", query, cursor)
                return [], None

        async for item in self.paginated_fetch(fetch_page, limit=limit):
            yield item

    def _handle_fetch_error(
        self, entity_type: str, query: str | None, cursor: str | None = None
    ) -> None:
        """Handle fetch errors centrally."""
        log_adapter_error(
            logger,
            provider="uniprot",
            operation=f"{entity_type} fetch",
            query=query,
            cursor=cursor,
        )
        if self.strict_error_handling:
            raise

    async def _get_features_json(self, query: str) -> list[dict[str, Any]]:
        """Retrieve features JSON."""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/uniprotkb/{query}.json"
            )
            if response.status_code == 200:
                return response.json().get("features", [])
            return []
        except Exception:
            self._handle_fetch_error("feature", query)
            return []

    async def _fetch_features(
        self,
        query: str | None,
        watermark: Watermark | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein features from UniProt."""
        if not query:
            raise ValueError("Query is required for feature search")

        # Watermark not supported for features
        if watermark:
            logger.warning("Watermark is not supported for feature fetch, ignoring.")

        features = await self._get_features_json(query)
        for i, feature in enumerate(features):
            if limit and i >= limit:
                break
            yield self._format_feature(query, feature)

    def _format_feature(self, query: str, feature: dict[str, Any]) -> dict[str, Any]:
        """Format a single feature."""
        return {
            "accession": query,
            "type": feature.get("type"),
            "location": feature.get("location"),
            "description": feature.get("description"),
        }

    async def _get_sequence_fasta(self, query: str) -> str | None:
        """Retrieve FASTA sequence."""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/uniprotkb/stream",
                params={"query": query, "format": "fasta"},
            )
            if response.status_code == 200:
                return response.text
            return None
        except Exception:
            self._handle_fetch_error("sequence", query)
            return None

    async def _get_parsed_sequences(self, query: str) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed sequences."""
        fasta_text = await self._get_sequence_fasta(query)
        if fasta_text:
            loop = asyncio.get_running_loop()
            seqs = await loop.run_in_executor(None, self._parse_fasta, fasta_text)
            for seq in seqs:
                yield seq

    async def _fetch_sequences(
        self,
        query: str | None,
        watermark: Watermark | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein sequences from UniProt."""
        if not query:
            raise ValueError("Query is required for sequence fetch")

        # Watermark not supported for sequences in this mode
        if watermark:
            logger.warning("Watermark is not supported for sequence fetch, ignoring.")

        fetched = 0
        async for seq_record in self._get_parsed_sequences(query):
            if limit and fetched >= limit:
                break
            yield seq_record
            fetched += 1

    def _parse_fasta(self, fasta_text: str) -> list[dict[str, Any]]:
        """Parse FASTA format text."""
        records = []
        current_header = None
        current_sequence: list[str] = []

        def add_record(header: str | None, seq: list[str]) -> None:
            if header:
                records.append({"header": header, "sequence": "".join(seq)})

        for line in fasta_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                add_record(current_header, current_sequence)
                current_header = line[1:]
                current_sequence = []
            else:
                current_sequence.append(line)

        add_record(current_header, current_sequence)
        return records

    async def health_check(self) -> HealthStatus:
        """Check UniProt API health status using a lightweight search query."""
        try:
            # Lightweight search probe: Ubiquitin (P62988)
            params = {"query": "accession:P622988", "size": 1, "format": "json"}
            resp = await self.http_client.get(
                f"{self.base_url}/uniprotkb/search", params=params
            )
            if resp.status_code != 200:
                return HealthStatus.DEGRADED
        except Exception:
            pass  # Fallback to circuit breaker check

        return await super().health_check()

    def __repr__(self) -> str:
        """String representation."""
        has_key = "with API key" if self.api_key else "without API key"
        return f"UniProtClient(base_url='{self.base_url}', {has_key})"
