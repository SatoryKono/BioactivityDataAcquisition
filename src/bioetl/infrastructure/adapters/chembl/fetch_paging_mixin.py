# mypy: disable-error-code=attr-defined
"""Pagination and filter-query helpers for ChEMBL fetch flows."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, NoReturn, cast

import httpx

from bioetl.domain.exceptions import (
    BioETLError,
    ExternalServiceError,
    RetryExhaustedError,
)
from bioetl.domain.types import BronzeRecord, JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.chembl.entity_mapper import (
        ChemblEntityMapper,
    )
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

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


class ChemblFetchPagingMixin:
    """Provides ChEMBL pagination and filtered-page iteration helpers."""

    # Host-class attributes (provided by ChemblAdapter.__init__)
    logger: LoggerPort
    provider_name: str
    _mapper: ChemblEntityMapper
    _adapter_metrics: AdapterMetricsRecorder
    http_client: UnifiedHTTPClient
    _request_collector: APIRequestCollector
    _compute_composite_key: Callable[[BronzeRecord, tuple[str, ...]], str]

    async def _fetch_page(
        self,
        url: str,
        params: JsonDict,
        entity_type: str,
    ) -> tuple[list[BronzeRecord], bool]:
        """Fetch a single page and handle errors.

        Args:
            url: Full API endpoint URL to request.
            params: Query parameters to include in the request.
            entity_type: ChEMBL entity type (e.g., ``"activity"``); used
                for metrics labeling and response parsing.

        Returns:
            Tuple of (list of records for the page, whether there is a next page).
        """
        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request(f"/{entity_type}"):
                response = await self._http_client.get(url, params=params)
            duration_ms = (time.perf_counter() - start_time) * 1000

            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            records, has_next = self._process_response(response, entity_type)
            return records, has_next
        except CHEMBL_ADAPTER_ERRORS as error:
            handle_error = cast("Callable[[Exception], NoReturn]", self._handle_error)
            handle_error(error)

    async def _page_iterator(
        self,
        entity_type: str,
        limit: int | None = None,
        start_offset: int = 0,
    ) -> AsyncIterator[list[BronzeRecord]]:
        """Yield pages of records.

        Args:
            entity_type: ChEMBL entity type (e.g., ``"activity"``).
            limit: Maximum total records to yield across all pages, or None for all.
            start_offset: Initial pagination offset (default 0).

        Returns:
            Async iterator of record lists, one list per API page.
        """
        url = self._mapper.get_resource_url(entity_type)
        offset = start_offset
        records_yielded = 0
        while True:
            params = self._build_params(offset, entity_type)
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
            offset += len(records)

    def _yield_deduplicated(
        self,
        records: list[BronzeRecord],
        seen_ids: set[str],
        pk_field: str,
        entity_type: str,
        filter_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> Iterator[BronzeRecord]:
        """Yield records while tracking seen IDs for deduplication.

        Args:
            records: Raw records from a single API page.
            seen_ids: Mutable set of already-yielded record identifiers;
                updated in place as new records are emitted.
            pk_field: Primary key field name for single-key deduplication.
            entity_type: ChEMBL entity type; used for metrics and logging.
            filter_field: Filter field name included in duplicate-skip log events.
            pk_fields: Optional tuple of field names for composite-key deduplication;
                when None or length 1, single-key logic is used.

        Returns:
            Iterator of unique BronzeRecord dicts not yet seen.
        """
        use_composite = pk_fields is not None and len(pk_fields) > 1

        for record in records:
            if use_composite:
                assert pk_fields is not None
                composite_key = self._compute_composite_key(record, pk_fields)
                if not composite_key or composite_key == "|".join(
                    [""] * len(pk_fields)
                ):
                    yield record
                    continue
                if composite_key in seen_ids:
                    self._logger.debug(
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
                    self._logger.debug(
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
        self,
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
        """Continue pagination after first filtered page.

        Args:
            url: Full API endpoint URL to paginate.
            id_batch: List of IDs already applied as the filter.
            filter_field: API field name used for filtering.
            entity_type: ChEMBL entity type (e.g., ``"activity"``).
            pk_field: Primary key field for single-key deduplication.
            seen_ids: Mutable set of already-yielded identifiers; shared across pages.
            start_offset: Pagination offset to begin from (i.e., length of first page).
            limit: Maximum total records already fetched, or None for no limit.
            pk_fields: Optional composite-key tuple; None for single-key dedup.

        Returns:
            Async iterator of additional deduplicated BronzeRecord dicts.
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
                self._logger.warning(
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
        self,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records filtered by ID batch with client-side deduplication.

        Args:
            entity_type: ChEMBL entity type (e.g., ``"activity"``).
            id_batch: List of IDs to include in the filter query.
            filter_field: API field name to filter on.
            limit: Maximum records to fetch, or None for no limit.

        Returns:
            Async iterator of deduplicated BronzeRecord dicts for the given batch.
        """
        url = self._mapper.get_resource_url(entity_type)
        seen_ids: set[str] = set()
        pk_field = self._get_api_pk_field(entity_type)
        pk_fields = self._get_api_dedup_fields(entity_type)

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


__all__ = ["CHEMBL_ADAPTER_ERRORS", "ChemblFetchPagingMixin"]
