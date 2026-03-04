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

__all__ = ["UNIPROT_BATCH_SIZE", "UNIPROT_FETCH_ERRORS", "UniProtAdapter"]


import asyncio
import contextlib
import time
from typing import TYPE_CHECKING, Any

from httpx import HTTPStatusError, RequestError
from typing_extensions import override

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.common import (
    run_fetch_with_fallback_policy,
    split_filter_ids_for_fallback,
)
from bioetl.infrastructure.adapters.http.pagination import PaginatedFetcherMixin
from bioetl.infrastructure.adapters.uniprot.fallback_resolver import (
    iter_uniprot_fallback_records,
    resolve_uniprot_missing_ids,
)
from bioetl.infrastructure.adapters.uniprot.fasta_parser import FastaParser
from bioetl.infrastructure.adapters.uniprot.health_probe import probe_uniprot_health
from bioetl.infrastructure.adapters.uniprot.metadata_adapter_mixin import (
    UniProtAdapterMetadataMixin,
)
from bioetl.infrastructure.adapters.uniprot.query_builder import (
    build_uniprot_protein_search_params,
)
from bioetl.infrastructure.adapters.uniprot.response_parser import (
    parse_uniprot_protein_response,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import httpx

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

# Maximum IDs per batch for UniProt OR-query (API recommendation)
UNIPROT_BATCH_SIZE = 100

# Fields to request from UniProt protein API
_PROTEIN_FETCH_FIELDS: tuple[str, ...] = (
    "accession",
    "id",
    "protein_name",
    "gene_names",  # identifiers
    "organism_name",
    "organism_id",
    "lineage",
    "sequence",
    "length",
    "mass",
    "protein_existence",
    "annotation_score",
    "reviewed",  # quality
    "date_created",
    "date_modified",
    "version",  # metadata
    "cc_function",
    "cc_catalytic_activity",
    "cc_activity_regulation",  # comments
    "cc_subunit",
    "cc_pathway",
    "cc_subcellular_location",
    "cc_tissue_specificity",
    "cc_alternative_products",
    "cc_disease",
    "cc_cofactor",
    "ph_dependence",
    "temp_dependence",
    "kinetics",
    "absorption",
    "redox_potential",
    "cc_induction",
    "cc_caution",
    "cc_similarity",
    "cc_pharmaceutical",
    "ft_domain",
    "ft_binding",
    "ft_site",
    "ft_act_site",
    "ft_mod_res",  # features
    "xref_pdb",
    "xref_chembl",
    "xref_drugbank",
    "xref_guidetopharmacology",
    "go_id",
    "xref_interpro",
    "xref_pfam",
    "xref_reactome",
    "keyword",  # xrefs
)

UNIPROT_FETCH_ERRORS = (
    BioETLError,
    NetworkError,
    RequestError,
    HTTPStatusError,
    ConnectionError,
    TimeoutError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
)


class _UniProtFallbackPolicyHandler:
    """Adapter-specific fallback hooks for shared fetch/fallback orchestration."""

    def __init__(self, adapter: UniProtAdapter, entity_type: str) -> None:
        self._adapter = adapter
        self._entity_type = entity_type

    async def process_missing_dois(
        self,
        *,
        dois: list[str],
        found_dois: set[str],
        fallback_mapping: dict[str, str],
        normalize_fn: Any,  # Any: compatibility with shared hook signature
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Process unresolved primary IDs through UniProt fallback search."""
        del normalize_fn
        missing_ids = self._adapter._should_do_fallback(
            dois,
            found_dois,
            fallback_mapping,
        )
        if not missing_ids:
            return
        async for record in self._adapter._do_fallback_search(
            self._entity_type,
            missing_ids,
            fallback_mapping,
            limit,
            fetched,
        ):
            yield record

    async def process_title_only_entries(
        self,
        *,
        entries: list[str],
        fallback_mapping: dict[str, str],
        limit: int | None,
        fetched: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Process title-only marker entries for legacy empty-ID fallback keys."""
        if not entries:
            return

        fallback_ids: list[str] = []
        seen_ids: set[str] = set()
        for entry in entries:
            fallback_id = entry if entry in fallback_mapping else ""
            if fallback_id not in fallback_mapping:
                continue
            if fallback_id in seen_ids:
                continue
            seen_ids.add(fallback_id)
            fallback_ids.append(fallback_id)

        if not fallback_ids:
            return
        async for record in self._adapter._do_fallback_search(
            self._entity_type,
            fallback_ids,
            fallback_mapping,
            limit,
            fetched,
        ):
            yield record


class UniProtAdapter(
    UniProtAdapterMetadataMixin, BaseHttpAdapter, PaginatedFetcherMixin
):
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
    ) -> None:
        """Initialize UniProt client.

        Args:
            http_client: Injected UnifiedHTTPClient
            logger: LoggerPort instance for structured logging
            api_key: UniProt API key (optional)
            base_url: UniProt REST API base URL
            strict_error_handling: Whether to raise exceptions (True) or log warnings (False)
            metrics: MetricsPort instance for recording SLA metrics

        """
        super().__init__(http_client, logger, metrics=metrics)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.strict_error_handling = strict_error_handling
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
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records from UniProt.

        If filter_ids are provided, builds an OR-query to fetch specific accessions.
        Otherwise fetches all records matching the query.

        Args:
            entity_type: Entity type identifier.
            limit: Maximum number of records to process.
            query: Search query string.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            offset: Offset.

        Returns:
            Async iterator yielding fetched records.
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
        strategy: Any,  # Any: callable fetch strategy (async generator factory)
        filter_ids: list[str],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
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
        strategy: Any,  # Any: callable fetch strategy (async generator factory)
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
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
    ) -> AsyncIterator[BronzeRecord]:
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

        Returns:
            Async iterator yielding fetched records.
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
    ) -> AsyncIterator[BronzeRecord]:
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

        Returns:
            Async iterator yielding fetched records.
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
    ) -> AsyncIterator[BronzeRecord]:
        """Search missing IDs via fallback mapping."""
        strategy = self._fetch_strategies.get(entity_type)
        if not strategy:
            return

        async for record in iter_uniprot_fallback_records(
            strategy=strategy,
            missing_ids=missing_ids,
            fallback_mapping=fallback_mapping,
            limit=limit,
            already_fetched=already_fetched,
        ):
            yield record

    async def _do_primary_fetch(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[tuple[BronzeRecord, str | None]]:
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
        """Determine IDs that require fallback search."""
        return resolve_uniprot_missing_ids(
            filter_ids=filter_ids,
            found_ids=found_ids,
            fallback_mapping=fallback_mapping,
        )

    @staticmethod
    def _deduplicate_filter_ids(filter_ids: list[str]) -> list[str]:
        """Deduplicate input IDs preserving original order."""
        unique_ids: list[str] = []
        seen_ids: set[str] = set()
        for filter_id in filter_ids:
            if filter_id in seen_ids:
                continue
            seen_ids.add(filter_id)
            unique_ids.append(filter_id)
        return unique_ids

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records with primary lookup and fallback search."""
        if not filter_ids:
            return

        requested_ids = self._deduplicate_filter_ids(filter_ids)
        primary_ids, title_only_entries = split_filter_ids_for_fallback(requested_ids)
        fallback_handler = _UniProtFallbackPolicyHandler(self, entity_type)

        async def _primary_records() -> AsyncIterator[BronzeRecord]:
            async for record, _ in self._do_primary_fetch(
                entity_type, primary_ids, filter_field, limit
            ):
                yield record

        def _extract_accession(record: BronzeRecord) -> str | None:
            accession = record.get("accession")
            if not isinstance(accession, str):
                return None
            normalized = accession.strip()
            return normalized if normalized else None

        async for record in run_fetch_with_fallback_policy(
            primary_records=_primary_records(),
            primary_ids=primary_ids,
            title_only_entries=title_only_entries,
            fallback_mapping=fallback_mapping,
            normalize_id=lambda value: value.strip(),
            extract_record_id=_extract_accession,
            fallback_handler=fallback_handler,
            limit=limit,
        ):
            yield record

    def _build_protein_fetch_params(
        self, query: str, size: int, fetched: int, limit: int | None, cursor: str | None
    ) -> dict[str, Any]:  # Any: HTTP query params (str|int|bool values)
        """Build the parameter dictionary for a protein fetch request."""
        return build_uniprot_protein_search_params(
            query=query,
            fetched=fetched,
            limit=limit,
            cursor=cursor,
            size=size,
            fields=_PROTEIN_FETCH_FIELDS,
        )

    def _parse_response(
        self, response: httpx.Response
    ) -> tuple[list[BronzeRecord], str | None]:
        """Process the HTTP response from a protein fetch request."""
        return parse_uniprot_protein_response(response)

    async def _fetch_proteins(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch protein entries from UniProt."""
        query = query or "*"
        size = 500

        async def _pagination_callback(
            cursor: str | None, fetched: int
        ) -> tuple[list[BronzeRecord], str | None]:
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
            except UNIPROT_FETCH_ERRORS as e:
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

    async def _get_features_json(self, query: str) -> list[BronzeRecord]:
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
                features: list[BronzeRecord] = response.json().get(
                    "features", []
                )  # Any: untyped UniProt API JSON response
                return features
            return []
        except UNIPROT_FETCH_ERRORS as e:
            self._handle_fetch_error("feature", query, error=e)
            return []

    async def _fetch_features(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch protein features from UniProt."""
        if not query:
            raise ValueError("Query is required for feature search")

        features = await self._get_features_json(query)
        for i, feature in enumerate(features):
            if limit and i >= limit:
                break
            yield self._format_feature(query, feature)

    def _format_feature(self, query: str, feature: BronzeRecord) -> BronzeRecord:
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
        except UNIPROT_FETCH_ERRORS as e:
            self._handle_fetch_error("sequence", query, error=e)
            return None

    async def _get_parsed_sequences(self, query: str) -> AsyncIterator[BronzeRecord]:
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
    ) -> AsyncIterator[BronzeRecord]:
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
            return await probe_uniprot_health(
                base_url=self.base_url,
                provider_name=self.provider_name,
                http_client=self.http_client,
                logger=self.logger,
                adapter_metrics=self._adapter_metrics,
                healthy_status_provider=self._fallback_health_status,
            )
        except UNIPROT_FETCH_ERRORS as e:
            error_type = self._error_handler.get_error_type(e)
            self.logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error_type=error_type.value,
                error=str(e),
            )
            raise
