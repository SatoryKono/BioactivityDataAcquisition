"""UniProt API client adapter.

Implements RULES.md Appendix A - UniProt specifications.

Requirements:
- Uses httpx for async REST API access
- Rate limit: 100 req/sec (with API key)
- Health check: Search probe (Ubiquitin)
- Entities: proteins, features, sequences

Documentation: https://www.uniprot.org/help/api
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING, Any

from typing_extensions import override

from bioetl.domain.ports import NoOpMetrics
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin
from bioetl.infrastructure.adapters.uniprot.fasta_parser import FastaParser

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import httpx

    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import LoggerPort, MetricsPort, CircuitBreakerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


# Maximum IDs per batch for UniProt OR-query (API recommendation)
UNIPROT_BATCH_SIZE = 100


class UniProtAdapter(BaseHttpAdapter, PaginatedFetcherMixin):
    """UniProt API adapter implementing DataSourcePort.

    Provides access to protein sequence and functional information from UniProt database.
    """

    provider_name: str = "uniprot"

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        api_key: str | None = None,
        base_url: str = "https://rest.uniprot.org",
        strict_error_handling: bool = False,
        metrics: MetricsPort | None = None,
        circuit_breaker: CircuitBreakerPort | None = None,
    ) -> None:
        """Initialize UniProt client.

        Args:
            http_client: Injected UnifiedHTTPClient
            logger: LoggerPort instance for structured logging
            api_key: UniProt API key (optional)
            base_url: UniProt REST API base URL
            strict_error_handling: Whether to raise exceptions (True) or log warnings (False)
            metrics: MetricsPort instance for recording SLA metrics
            circuit_breaker: CircuitBreakerPort instance (optional)

        """
        super().__init__(http_client, logger, metrics=metrics, circuit_breaker=circuit_breaker)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.strict_error_handling = strict_error_handling
        metrics_port = metrics if metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)
        self._request_collector = APIRequestCollector()
        self._fetch_strategies = {
            "protein": self._fetch_proteins,
            "feature": self._fetch_features,
            "sequence": self._fetch_sequences,
        }

    @override
    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from UniProt.

        If filter_ids are provided, builds an OR-query to fetch specific accessions.
        Otherwise fetches all records matching the query.
        """
        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        # If filter_ids provided, use filtered fetch
        if filter_ids and filter_field:
            async for record in self.fetch_filtered(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                yield record
        else:
            # Standard fetch with optional query
            async for record in strategy(query=query, limit=limit):
                yield record

    async def _fetch_non_protein_filtered(
        self,
        strategy: Any,
        filter_ids: list[str],
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch non-protein entities by iterating through individual IDs.

        Args:
            strategy: The fetch strategy function to use.
            filter_ids: List of IDs to fetch.
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records for each ID.
        """
        fetched = 0
        for acc_id in filter_ids:
            if limit and fetched >= limit:
                break
            async for record in strategy(query=acc_id, limit=1):
                yield record
                fetched += 1
                if limit and fetched >= limit:
                    break

    async def _fetch_proteins_batched(
        self,
        strategy: Any,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch proteins using batched OR-queries.

        Args:
            strategy: The protein fetch strategy function.
            filter_ids: List of accession IDs to fetch.
            filter_field: Field name for filtering (typically 'accession').
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records matching the filter criteria.
        """
        fetched = 0
        for batch_start in range(0, len(filter_ids), UNIPROT_BATCH_SIZE):
            if limit and fetched >= limit:
                break

            batch = filter_ids[batch_start : batch_start + UNIPROT_BATCH_SIZE]
            or_query = " OR ".join(f"{filter_field}:{acc}" for acc in batch)

            batch_limit = (limit - fetched) if limit else None
            async for record in strategy(query=or_query, limit=batch_limit):
                yield record
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from UniProt filtered by specific IDs.

        Implements FilterableDataSourcePort.fetch_filtered().

        Builds OR-query for UniProt API: accession:P12345 OR accession:Q67890
        Processes IDs in batches to avoid query length limits.

        Args:
            entity_type: Type of entity to fetch (protein, feature, sequence)
            filter_ids: List of IDs to filter by
            filter_field: Field name to filter on (typically 'accession')
            limit: Maximum number of records to fetch

        Yields:
            Dictionary records matching the filter criteria

        """
        if not filter_ids:
            return

        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        if entity_type != "protein":
            async for record in self._fetch_non_protein_filtered(
                strategy, filter_ids, limit
            ):
                yield record
        else:
            async for record in self._fetch_proteins_batched(
                strategy, filter_ids, filter_field, limit
            ):
                yield record

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from UniProt filtered by multiple fields (AND logic).

        Implements FilterableDataSourcePort.fetch_multi_filtered().

        Builds AND-query for UniProt API combining multiple filter conditions.
        Example: (accession:P12345 OR accession:Q67890) AND (organism_id:9606)

        Args:
            entity_type: Type of entity to fetch
            filters: Mapping from filter_field to list of IDs
            limit: Maximum number of records to fetch

        Yields:
            Dictionary records matching ALL filter criteria

        """
        if not filters:
            return

        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported: {', '.join(self._fetch_strategies.keys())}"
            )

        # Build AND-query from multiple filter conditions
        and_parts: list[str] = []
        for field, ids in filters.items():
            if not ids:
                continue
            # Build OR-part for this field
            or_part = " OR ".join(f"{field}:{val}" for val in ids)
            and_parts.append(f"({or_part})")

        if not and_parts:
            return

        combined_query = " AND ".join(and_parts)
        async for record in strategy(query=combined_query, limit=limit):
            yield record

    async def _do_fallback_search(
        self,
        entity_type: str,
        missing_ids: list[str],
        fallback_mapping: dict[str, str],
        limit: int | None,
        already_fetched: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Search for missing IDs using fallback values.

        Args:
            entity_type: Type of entity to fetch.
            missing_ids: IDs not found in primary lookup.
            fallback_mapping: Mapping from primary ID to fallback value.
            limit: Maximum total records to fetch.
            already_fetched: Number of records already yielded.

        Yields:
            Dictionary records found via fallback search.
        """
        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            return

        fetched = already_fetched
        for missing_id in missing_ids:
            if limit and fetched >= limit:
                break

            fallback_value = fallback_mapping.get(missing_id)
            if not fallback_value:
                continue

            async for record in strategy(query=fallback_value, limit=1):
                yield record
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def _do_primary_fetch(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[tuple[dict[str, Any], str | None]]:
        """Perform primary fetch and yield records with their accessions.

        Args:
            entity_type: Type of entity to fetch.
            filter_ids: List of primary IDs to filter by.
            filter_field: Field name for primary filtering.
            limit: Maximum number of records to fetch.

        Yields:
            Tuples of (record, accession) for each fetched record.
        """
        async for record in self.fetch_filtered(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=limit,
        ):
            yield record, record.get("accession")

    def _should_do_fallback(
        self,
        filter_ids: list[str],
        found_ids: set[str],
        fallback_mapping: dict[str, str],
    ) -> list[str]:
        """Determine which IDs need fallback search.

        Args:
            filter_ids: Original list of IDs requested.
            found_ids: Set of IDs successfully found.
            fallback_mapping: Mapping for fallback values.

        Returns:
            List of missing IDs that have fallback values, or empty list.
        """
        if not fallback_mapping:
            return []
        return [fid for fid in filter_ids if fid not in found_ids]

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records with fallback search when primary lookup fails.

        Implements FilterableDataSourcePort.fetch_filtered_with_fallback().

        UniProt accessions are stable identifiers, so fallback is rarely needed.
        This method first tries the primary lookup, then falls back to search
        for any IDs not found.

        Args:
            entity_type: Type of entity to fetch
            filter_ids: List of primary IDs to filter by
            filter_field: Field name for primary filtering
            fallback_mapping: Mapping from primary ID to fallback value (e.g., gene name)
            limit: Maximum number of records to fetch

        Yields:
            Dictionary records found via primary lookup or fallback search

        """
        if not filter_ids:
            return

        fetched = 0
        found_ids: set[str] = set()

        async for record, accession in self._do_primary_fetch(
            entity_type, filter_ids, filter_field, limit
        ):
            yield record
            fetched += 1
            if accession:
                found_ids.add(accession)
            if limit and fetched >= limit:
                return

        missing_ids = self._should_do_fallback(filter_ids, found_ids, fallback_mapping)
        if not missing_ids:
            return

        async for record in self._do_fallback_search(
            entity_type, missing_ids, fallback_mapping, limit, fetched
        ):
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

    def _parse_response(
        self, response: httpx.Response
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Process the HTTP response from a protein fetch request."""
        if response.status_code != 200:
            return [], None
        data = response.json()
        results = data.get("results", [])
        cursor = data.get("nextCursor")
        return results, cursor

    async def _fetch_proteins(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein entries from UniProt."""
        query = query or "*"
        size = 500

        async def _pagination_callback(
            cursor: str | None, fetched: int
        ) -> tuple[list[dict[str, Any]], str | None]:
            """Execute pagination callback."""
            params = self._build_protein_fetch_params(
                query, size, fetched, limit, cursor
            )
            try:
                start_time = time.perf_counter()
                with self._adapter_metrics.measure_request("/uniprotkb/search"):
                    response = await self.http_client.get(
                        f"{self.base_url}/uniprotkb/search", params=params
                    )
                duration_ms = (time.perf_counter() - start_time) * 1000
                # Record request (gracefully handle mocked responses in tests)
                with contextlib.suppress(Exception):
                    self._request_collector.record_from_response(response, duration_ms)
                return self._parse_response(response)
            except Exception as e:
                self._handle_fetch_error("protein", query, cursor, error=e)
                return [], None

        async for item in self.paginated_fetch(_pagination_callback, limit=limit):
            yield item

    def _handle_fetch_error(
        self,
        entity_type: str,
        query: str | None,
        cursor: str | None = None,
        error: Exception | None = None,
    ) -> None:
        """Handle fetch errors with unified error handling."""
        context = {"query": query, "cursor": cursor, "entity_type": entity_type}
        if error is not None:
            self._error_handler.log_error(
                provider=self.provider_name,
                operation=f"{entity_type}_fetch",
                error=error,
                context=context,
            )
        else:
            self.logger.error(
                "external_api_error",
                provider=self.provider_name,
                operation=f"{entity_type}_fetch",
                **context,
            )
        if self.strict_error_handling and error is not None:
            wrapped = self._error_handler.wrap_error(
                error=error, provider=self.provider_name
            )
            raise wrapped from error

    async def _get_features_json(self, query: str) -> list[dict[str, Any]]:
        """Retrieve features JSON."""
        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request("/uniprotkb/features"):
                response = await self.http_client.get(
                    f"{self.base_url}/uniprotkb/{query}.json"
                )
            duration_ms = (time.perf_counter() - start_time) * 1000
            # Record request (gracefully handle mocked responses in tests)
            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)
            if response.status_code == 200:
                features: list[dict[str, Any]] = response.json().get("features", [])
                return features
            return []
        except Exception as e:
            self._handle_fetch_error("feature", query, error=e)
            return []

    async def _fetch_features(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein features from UniProt."""
        if not query:
            raise ValueError("Query is required for feature search")

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
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request("/uniprotkb/stream"):
                response = await self.http_client.get(
                    f"{self.base_url}/uniprotkb/stream",
                    params={"query": query, "format": "fasta"},
                )
            duration_ms = (time.perf_counter() - start_time) * 1000
            # Record request (gracefully handle mocked responses in tests)
            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)
            if response.status_code == 200:
                text: str = response.text
                return text
            return None
        except Exception as e:
            self._handle_fetch_error("sequence", query, error=e)
            return None

    async def _get_parsed_sequences(self, query: str) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed sequences."""
        fasta_text = await self._get_sequence_fasta(query)
        if fasta_text:
            loop = asyncio.get_running_loop()
            seqs = await loop.run_in_executor(None, FastaParser.parse, fasta_text)
            for seq in seqs:
                yield seq

    async def _fetch_sequences(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch protein sequences from UniProt."""
        if not query:
            raise ValueError("Query is required for sequence fetch")

        fetched = 0
        async for seq_record in self._get_parsed_sequences(query):
            if limit and fetched >= limit:
                break
            yield seq_record
            fetched += 1

    @override
    async def _probe_health(self) -> HealthStatus:
        """Perform health probe using Ubiquitin P62988 query."""
        try:
            params = {"query": "accession:P62988", "size": 1, "format": "json"}
            with self._adapter_metrics.measure_request("/health"):
                resp = await self.http_client.get_once(
                    f"{self.base_url}/uniprotkb/search", params=params
                )
            if resp.status_code != 200:
                self.logger.warning(
                    "health_check_degraded",
                    provider=self.provider_name,
                    reason="non_200_response",
                    status_code=resp.status_code,
                )
                return HealthStatus.DEGRADED
            return self._fallback_health_status()
        except Exception as e:
            error_type = self._error_handler.get_error_type(e)
            self.logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error_type=error_type.value,
                error=str(e),
            )
            raise

    def _get_health_endpoint(self) -> str:
        """Return health check endpoint."""
        return "/uniprotkb/search"

    def __repr__(self) -> str:
        key_info = "with API key" if self.api_key else "without API key"
        return f"UniProtAdapter(base_url='{self.base_url}', {key_info})"

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Get API request metadata and clear collector."""
        metadata = self._request_collector.to_source_metadata(
            source_type="api", url=self.base_url, api_version=api_version
        )
        self._request_collector.clear()
        return metadata

    def clear_request_collector(self) -> None:
        """Clear the collector without returning metadata."""
        self._request_collector.clear()

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return self._request_collector.request_count
