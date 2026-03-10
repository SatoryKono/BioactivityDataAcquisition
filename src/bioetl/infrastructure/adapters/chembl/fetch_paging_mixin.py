"""Pagination and filter-query helpers for ChEMBL fetch flows."""

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

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.chembl.entity_mapper import ChemblEntityMapper
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
    _adapter_metrics: AdapterMetrics
    http_client: UnifiedHTTPClient
    _request_collector: APIRequestCollector
    _compute_composite_key: Callable[[BronzeRecord, tuple[str, ...]], str]
    _process_response: Callable[[httpx.Response, str], tuple[list[BronzeRecord], bool]]
    _handle_error: Callable[[Exception, str], None]
    _build_params: Callable[[int, str | None], dict[str, Any]]
    _build_filter_params: Callable[[str, str, list[str]], dict[str, str]]
    _get_api_pk_field: Callable[[str], str]
    _get_api_dedup_fields: Callable[[str], tuple[str, ...]]
    _normalize_filter_field: Callable[[str, str], str]
    _page_size: int

    async def _fetch_page(
        self: ChemblFetchPagingMixin,
        url: str,
        params: dict[str, Any],  # Any: HTTP query params (str|int|bool values)
        entity_type: str,
    ) -> tuple[list[BronzeRecord], bool]:
        """Fetch a single page and handle errors."""
        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request(f"/{entity_type}"):
                response = await self.http_client.get(url, params=params)
            duration_ms = (time.perf_counter() - start_time) * 1000

            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            records, has_next = self._process_response(response, entity_type)
            return records, has_next
        except CHEMBL_ADAPTER_ERRORS as error:
            handle_error = cast("Callable[[Exception], NoReturn]", self._handle_error)
            handle_error(error)

    async def _page_iterator(
        self: ChemblFetchPagingMixin,
        entity_type: str,
        limit: int | None = None,
        start_offset: int = 0,
    ) -> AsyncIterator[list[BronzeRecord]]:
        """Yield pages of records."""
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
        self: ChemblFetchPagingMixin,
        records: list[BronzeRecord],
        seen_ids: set[str],
        pk_field: str,
        entity_type: str,
        filter_field: str,
        pk_fields: tuple[str, ...] | None = None,
    ) -> Iterator[BronzeRecord]:
        """Yield records while tracking seen IDs for deduplication."""
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
        self: ChemblFetchPagingMixin,
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
        """Continue pagination after first filtered page."""
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
        self: ChemblFetchPagingMixin,
        entity_type: str,
        id_batch: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records filtered by ID batch with client-side deduplication."""
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
