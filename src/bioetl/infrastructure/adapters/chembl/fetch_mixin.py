"""Fetch pipeline mixin for ChEMBL adapter."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, NoReturn, cast

import httpx

from bioetl.domain.exceptions import (
    BioETLError,
    ExternalServiceError,
    RetryExhaustedError,
)
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.chembl.fetch_multi_filter_mixin import (
    ChemblFetchMultiFilterMixin,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

CHEMBL_ADAPTER_ERRORS = (
    BioETLError,
    ExternalServiceError,
    RetryExhaustedError,
    httpx.HTTPError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
    AttributeError,
    Exception,
)


class ChemblFetchMixin(ChemblFetchMultiFilterMixin):
    """Provides ChEMBL pagination, filtering, and retry fetch flows."""

    async def _fetch_page(
        self: Any,  # Any: mixin self type
        url: str,
        params: dict[str, Any],  # Any: HTTP query params (str|int|bool values)
        entity_type: str,
    ) -> tuple[list[BronzeRecord], bool]:
        """Fetch a single page and handle errors.

        Note: Success/failure tracking is handled by the circuit breaker
        in UnifiedHTTPClient, no duplicate tracking needed here.

        Records request metadata via APIRequestCollector for Bronze layer enrichment.
        """
        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request(f"/{entity_type}"):
                response = await self.http_client.get(url, params=params)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record request for metadata enrichment (gracefully handle mocked responses)
            # Skip recording if response doesn't have expected attributes
            # (e.g., during testing with mocked responses or validation errors)
            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            records, has_next = self._process_response(response, entity_type)
            return records, has_next
        except CHEMBL_ADAPTER_ERRORS as e:
            handle_error = cast("Callable[[Exception], NoReturn]", self._handle_error)
            handle_error(e)

    async def _page_iterator(
        self: Any,  # Any: mixin self type
        entity_type: str,
        limit: int | None = None,
        start_offset: int = 0,
    ) -> AsyncIterator[list[BronzeRecord]]:
        """Yield pages of records.

        Args:
            entity_type: Type of entity to fetch.
            limit: Maximum number of records to yield.
            start_offset: API offset to start fetching from (for checkpoint resume).
        """
        url = self._mapper.get_resource_url(entity_type)
        offset = start_offset
        records_yielded = 0
        while True:
            params = self._build_params(offset, entity_type)
            # Optimize limit: if we have a global limit and it's smaller than effective batch size
            # Skip for entities that don't support pagination
            if limit is not None and "limit" in params:
                remaining = limit - records_yielded
                if remaining > 0:
                    params["limit"] = min(params["limit"], remaining)
                elif remaining <= 0:
                    break

            records, has_next = await self._fetch_page(url, params, entity_type)
            if not records:
                break
            yield records
            records_yielded += len(records)
            if not has_next:
                break
            # Fix: increment by actual records fetched to handle dynamic limits correctly
            offset += len(records)

    def _yield_deduplicated(
        self: Any,  # Any: mixin self type
        records: list[BronzeRecord],
        seen_ids: set[str],
        pk_field: str,
        entity_type: str,
        filter_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> Iterator[BronzeRecord]:
        """Yield records while tracking seen IDs for deduplication.

        Supports both single field and composite key deduplication.
        If pk_fields is provided with multiple fields, uses composite key.

        Args:
            records: List of records to deduplicate.
            seen_ids: Set of already seen keys (mutated in place).
            pk_field: Single primary key field (used if pk_fields has single field).
            entity_type: Entity type for logging.
            filter_field: Filter field for logging context.
            pk_fields: Composite primary key fields. If len > 1, uses composite dedup.
        """
        use_composite = pk_fields is not None and len(pk_fields) > 1

        for record in records:
            if use_composite:
                # Type narrowing: pk_fields is not None when use_composite is True
                assert pk_fields is not None
                composite_key = self._compute_composite_key(record, pk_fields)
                if not composite_key or composite_key == "|".join(
                    [""] * len(pk_fields)
                ):
                    # Skip records with empty composite key
                    yield record
                    continue
                if composite_key in seen_ids:
                    self.logger.debug(
                        "skipping_duplicate_record",
                        entity_type=entity_type,
                        pk_fields=pk_fields,
                        composite_key=composite_key,
                        filter_field=filter_field,
                    )
                    self._adapter_metrics.record_dropped_duplicates(entity_type)
                    continue
                seen_ids.add(composite_key)
            else:
                record_id = str(record.get(pk_field, ""))
                if record_id and record_id in seen_ids:
                    self.logger.debug(
                        "skipping_duplicate_record",
                        entity_type=entity_type,
                        pk_field=pk_field,
                        record_id=record_id,
                        filter_field=filter_field,
                    )
                    self._adapter_metrics.record_dropped_duplicates(entity_type)
                    continue
                if record_id:
                    seen_ids.add(record_id)
            yield record

    async def _paginate_filter_results(
        self: Any,  # Any: mixin self type
        url: str,
        id_batch: list[str],
        filter_field: str,
        entity_type: str,
        pk_field: str,
        seen_ids: set[str],
        start_offset: int,
        limit: int | None,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Continue pagination after first page.

        Args:
            url: API URL.
            id_batch: Batch of IDs to filter by.
            filter_field: Field to filter on.
            entity_type: Entity type for logging.
            pk_field: Single primary key field (backward compatibility).
            seen_ids: Set of already seen keys.
            start_offset: Starting offset for pagination.
            limit: Maximum records to fetch.
            pk_fields: Composite primary key fields for deduplication.
        """
        offset = start_offset
        while True:
            if limit and offset >= limit:
                break
            params = self._build_params(offset, entity_type)
            params.update(
                self._build_filter_params(entity_type, filter_field, id_batch)
            )
            try:
                records, has_next = await self._fetch_page(url, params, entity_type)
            except CHEMBL_ADAPTER_ERRORS:
                # Catch all: API errors (network, timeout, 500s, malformed response),
                # JSON decode errors, or validation failures. Log partial success and
                # gracefully terminate pagination to avoid data loss.
                self.logger.warning(
                    "chembl_pagination_interrupted",
                    entity_type=entity_type,
                    offset=offset,
                    records_yielded=len(seen_ids),
                )
                return
            if not records:
                break
            for record in self._yield_deduplicated(
                records, seen_ids, pk_field, entity_type, filter_field, pk_fields
            ):
                yield record
            if not has_next:
                break
            offset += len(records)

    async def _fetch_with_filter(
        self: Any,  # Any: mixin self type
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records filtered by ID batch with client-side deduplication.

        Uses composite key deduplication for entities with multiple primary key fields.
        """
        url = self._mapper.get_resource_url(entity_type)
        seen_ids: set[str] = set()
        pk_field = self._get_api_pk_field(entity_type)
        pk_fields = self._get_api_dedup_fields(entity_type)

        # Detect 1:1 PK filter: filter on entity's own single PK, batch fits in page.
        # N IDs → at most N records → no limit/offset pagination needed.
        # For 1:N (e.g. activity by molecule_id) pagination is preserved.
        api_filter_field = self._normalize_filter_field(entity_type, filter_field)
        skip_pagination = (
            len(pk_fields) == 1
            and pk_fields[0] == api_filter_field
            and len(id_batch) <= self._page_size
        )

        params = self._build_params(0, entity_type)
        if skip_pagination:
            params.pop("limit", None)
            params.pop("offset", None)
        params.update(self._build_filter_params(entity_type, filter_field, id_batch))

        records, has_next = await self._fetch_page(url, params, entity_type)

        if not records:
            return

        for record in self._yield_deduplicated(
            records, seen_ids, pk_field, entity_type, filter_field, pk_fields
        ):
            yield record

        if has_next:
            async for record in self._paginate_filter_results(
                url,
                id_batch,
                filter_field,
                entity_type,
                pk_field,
                seen_ids,
                len(records),
                limit,
                pk_fields,
            ):
                yield record

    def _handle_error(self: Any, e: Exception, context: str = "fetch") -> NoReturn:
        """Handle errors with unified classification. Translates to domain exceptions."""
        # Build context with circuit breaker info
        failure_count = self.http_client.circuit_breaker.get_failure_count()
        health_status = self._get_health_status()

        error_context = {
            "circuit_breaker_state": self.http_client.circuit_breaker.get_state().value,
            "circuit_breaker_failures": failure_count,
            "health_status": health_status.value,
        }

        # Use unified error handler
        wrapped = self._error_handler.handle_error(
            error=e,
            provider=self.provider_name,
            operation=context,
            context=error_context,
        )
        raise wrapped from e

    def _is_retry_exhausted_error(self: Any, e: Exception) -> bool:
        """Check if exception is a retry exhausted error (direct or wrapped)."""
        if isinstance(e, RetryExhaustedError):
            return True
        # Check if it's an ExternalServiceError wrapping RetryExhaustedError
        return isinstance(e, ExternalServiceError) and isinstance(
            e.__cause__, RetryExhaustedError
        )

    def _log_single_id_failure(
        self, entity_type: str, filter_field: str, id_batch: list[str], e: Exception
    ) -> None:
        """Log single ID fetch failure for graceful degradation."""
        failed_id = id_batch[0] if id_batch else "unknown"
        self.logger.error(
            "single_id_fetch_failed",
            provider=self.provider_name,
            entity_type=entity_type,
            filter_field=filter_field,
            failed_id=failed_id,
            error=str(e),
            error_class=type(e).__name__,
        )

    async def _fetch_single_record_direct(
        self, entity_type: str, record_id: str
    ) -> BronzeRecord | None:
        """Fetch a single record using direct endpoint as fallback.

        ChEMBL API has two code paths:
        1. Filter endpoint: /target?target_chembl_id__in=CHEMBL123 (may fail with 500)
        2. Direct endpoint: /target/CHEMBL123 (often works when filter fails)

        This method is used as a fallback when the filter endpoint fails for a single ID.

        Args:
            entity_type: Entity type to fetch.
            record_id: The ChEMBL ID of the record.

        Returns:
            Record dict if successful, None if failed.
        """
        direct_url = self._mapper.get_direct_record_url(entity_type, record_id)
        params = {"format": "json"}

        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request(f"/{entity_type}/{record_id}"):
                response = await self.http_client.get(direct_url, params=params)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record request for metadata enrichment
            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            # Direct endpoint returns single record, not wrapped in plural key
            data = response.json()

            # ChEMBL direct endpoint returns the record directly (not in a list)
            if isinstance(data, dict) and not data.get("page_meta"):
                self.logger.info(
                    "direct_endpoint_fallback_success",
                    entity_type=entity_type,
                    record_id=record_id,
                )
                return data

            return None

        except CHEMBL_ADAPTER_ERRORS as e:
            self.logger.warning(
                "direct_endpoint_fallback_failed",
                entity_type=entity_type,
                record_id=record_id,
                error=str(e),
                error_class=type(e).__name__,
            )
            return None

    async def _retry_with_split_batches(
        self: Any,  # Any: mixin self type
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        error: Exception,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Split failed batch in half and retry each part recursively."""
        mid = len(id_batch) // 2
        first_half, second_half = id_batch[:mid], id_batch[mid:]

        self.logger.warning(
            "batch_reduction_retry",
            provider=self.provider_name,
            entity_type=entity_type,
            original_batch_size=len(id_batch),
            first_half_size=len(first_half),
            second_half_size=len(second_half),
            filter_field=filter_field,
            error=str(error),
        )

        async for record in self._fetch_batch_with_reduction(
            entity_type, first_half, filter_field, limit, seen_ids, pk_field, pk_fields
        ):
            yield record
        async for record in self._fetch_batch_with_reduction(
            entity_type, second_half, filter_field, limit, seen_ids, pk_field, pk_fields
        ):
            yield record

    async def _fetch_batch_with_reduction(
        self: Any,  # Any: mixin self type
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None,
        seen_ids: set[str],
        pk_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch a batch of IDs with automatic batch size reduction on failures.

        Args:
            entity_type: Entity type to fetch.
            id_batch: Batch of IDs to filter by.
            filter_field: Field to filter on.
            limit: Maximum records to fetch.
            seen_ids: Set of already seen keys.
            pk_field: Single primary key field (backward compatibility).
            pk_fields: Composite primary key fields for deduplication.
        """
        use_composite = pk_fields is not None and len(pk_fields) > 1
        try:
            async for record in self._fetch_with_filter(
                entity_type, id_batch, filter_field, limit
            ):
                if use_composite:
                    # Type narrowing: pk_fields is not None when use_composite is True
                    assert pk_fields is not None
                    composite_key = self._compute_composite_key(record, pk_fields)
                    if not composite_key or composite_key in seen_ids:
                        continue
                    seen_ids.add(composite_key)
                else:
                    record_id = str(record.get(pk_field, ""))
                    if not record_id or record_id in seen_ids:
                        continue
                    seen_ids.add(record_id)
                yield record
        except (RetryExhaustedError, ExternalServiceError) as e:
            if not self._is_retry_exhausted_error(e):
                raise
            if len(id_batch) > 1:
                async for record in self._retry_with_split_batches(
                    entity_type,
                    id_batch,
                    filter_field,
                    limit,
                    seen_ids,
                    pk_field,
                    e,
                    pk_fields,
                ):
                    yield record
            else:
                # Filter endpoint failed for single ID - try direct endpoint fallback
                # ChEMBL filter and direct endpoints use different server code paths
                single_id = id_batch[0]
                direct_record = await self._fetch_single_record_direct(
                    entity_type, single_id
                )
                if direct_record is not None:
                    # Deduplicate and yield
                    if use_composite:
                        assert pk_fields is not None
                        composite_key = self._compute_composite_key(
                            direct_record, pk_fields
                        )
                        if composite_key and composite_key not in seen_ids:
                            seen_ids.add(composite_key)
                            yield direct_record
                    else:
                        record_pk = str(direct_record.get(pk_field, ""))
                        if record_pk and record_pk not in seen_ids:
                            seen_ids.add(record_pk)
                            yield direct_record
                else:
                    # Both filter and direct endpoints failed
                    self._log_single_id_failure(entity_type, filter_field, id_batch, e)

    async def _fetch_filtered(
        self: Any,  # Any: mixin self type
        entity_type: str,
        limit: int | None,
        filter_ids: list[str],
        filter_field: str,
    ) -> AsyncIterator[BronzeRecord]:
        """Perform filtered fetch using ID batches with client-side deduplication.

        Uses batch reduction strategy: on failures, splits batch in half
        and retries each part recursively until success or single-ID failure.
        Supports composite key deduplication for entities with multiple PK fields.
        """
        total_fetched = 0
        seen_ids: set[str] = set()
        pk_field = self._get_api_pk_field(entity_type)
        pk_fields = self._get_api_dedup_fields(entity_type)

        for id_batch in self._batch_ids(filter_ids, batch_size=self._filter_batch_size):
            async for record in self._fetch_batch_with_reduction(
                entity_type,
                id_batch,
                filter_field,
                limit,
                seen_ids,
                pk_field,
                pk_fields,
            ):
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

    async def _fetch_standard(
        self: Any,  # Any: mixin self type
        entity_type: str,
        limit: int | None,
        offset: int = 0,
    ) -> AsyncIterator[BronzeRecord]:
        """Perform standard paginated fetch with client-side deduplication."""
        total_fetched = 0
        seen_keys: set[str] = set()
        pk_field = self._get_api_pk_field(entity_type)
        pk_fields = self._get_api_dedup_fields(entity_type)
        use_composite = len(pk_fields) > 1

        async for records in self._page_iterator(
            entity_type, limit, start_offset=offset
        ):
            for record in records:
                if use_composite:
                    composite_key = self._compute_composite_key(record, pk_fields)
                    if composite_key and composite_key in seen_keys:
                        self.logger.debug(
                            "skipping_duplicate_record",
                            entity_type=entity_type,
                            pk_fields=pk_fields,
                            composite_key=composite_key,
                        )
                        self._adapter_metrics.record_dropped_duplicates(entity_type)
                        continue
                    if composite_key:
                        seen_keys.add(composite_key)
                else:
                    record_id = str(record.get(pk_field, ""))
                    if record_id and record_id in seen_keys:
                        self.logger.debug(
                            "skipping_duplicate_record",
                            entity_type=entity_type,
                            pk_field=pk_field,
                            record_id=record_id,
                        )
                        self._adapter_metrics.record_dropped_duplicates(entity_type)
                        continue
                    if record_id:
                        seen_keys.add(record_id)
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

    async def fetch(
        self: Any,  # Any: mixin self type
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records from ChEMBL.

        Implements DataSourcePort.fetch() interface.

        Args:
            entity_type: Type of entity to fetch (activity, assay, compound, etc.)
            limit: Maximum number of records to fetch
            query: Unused for ChEMBL
            filter_ids: List of IDs to filter by (for deterministic batching)
            filter_field: Field name to filter on
            offset: API offset to start from (for checkpoint resume)

        Yields:
            Dictionary records from ChEMBL API

        Returns:
            Async iterator yielding fetched records.
        """
        if filter_ids and filter_field:
            async for record in self._fetch_filtered(
                entity_type, limit, filter_ids, filter_field
            ):
                yield record
        else:
            async for record in self._fetch_standard(
                entity_type, limit, offset=offset or 0
            ):
                yield record

    async def fetch_filtered(
        self: Any,  # Any: mixin self type
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records from ChEMBL with ID filtering.

        Implements FilterableDataSourcePort.fetch_filtered().

        Args:
            entity_type: Type of entity to fetch
            filter_ids: Sorted list of IDs to filter by (for deterministic batching)
            filter_field: Field name to filter on
            limit: Maximum number of records to fetch

        Yields:
            Dictionary records matching the filter criteria

        Returns:
            Async iterator yielding fetched records.
        """
        async for record in self._fetch_filtered(
            entity_type, limit, filter_ids, filter_field
        ):
            yield record

    async def fetch_filtered_with_fallback(
        self: Any,  # Any: mixin self type
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch with fallback (ChEMBL IDs always resolvable, fallback ignored).

        Args:
            entity_type: Entity type identifier.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            fallback_mapping: Fallback mapping.
            limit: Maximum number of records to process.

        Returns:
            Async iterator yielding fetched records.
        """
        _ = fallback_mapping  # Unused - ChEMBL IDs are always resolvable
        async for record in self._fetch_filtered(
            entity_type, limit, filter_ids, filter_field
        ):
            yield record
