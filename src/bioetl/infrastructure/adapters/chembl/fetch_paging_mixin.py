# mypy: disable-error-code=attr-defined
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Pagination helpers for ChEMBL fetch flows."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, NoReturn, cast

from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.chembl._fetch_paging_filtered import (
    _ChemblFetchPagingFilteredMixin,
)
from bioetl.infrastructure.adapters.chembl._fetch_resilience_error import (
    CHEMBL_ADAPTER_ERRORS as _CHEMBL_ADAPTER_ERRORS,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.chembl.entity_mapper import (
        ChemblEntityMapper,
    )
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

CHEMBL_ADAPTER_ERRORS = _CHEMBL_ADAPTER_ERRORS


class ChemblFetchPagingMixin(_ChemblFetchPagingFilteredMixin):
    """Provides ChEMBL pagination and filtered-page iteration helpers."""

    CHEMBL_ADAPTER_ERRORS = _CHEMBL_ADAPTER_ERRORS

    # Host-class attributes (provided by ChemblAdapter.__init__)
    logger: LoggerPort  # pyright: ignore[reportUninitializedInstanceVariable]
    provider_name: str  # pyright: ignore[reportUninitializedInstanceVariable]
    _mapper: ChemblEntityMapper  # pyright: ignore[reportUninitializedInstanceVariable]
    _adapter_metrics: AdapterMetricsRecorder  # pyright: ignore[reportUninitializedInstanceVariable]
    http_client: UnifiedHTTPClient  # pyright: ignore[reportUninitializedInstanceVariable]
    _request_collector: APIRequestCollector  # pyright: ignore[reportUninitializedInstanceVariable]
    _compute_composite_key: Callable[[BronzeRecord, tuple[str, ...]], str]  # pyright: ignore[reportUninitializedInstanceVariable]

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
                response = await self.http_client.get(url, params=params)
            duration_ms = (time.perf_counter() - start_time) * 1000

            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            records, has_next = self._process_response(response, entity_type)  # pyright: ignore[reportAttributeAccessIssue]
            self._clear_probe_degraded_state_on_success()  # pyright: ignore[reportAttributeAccessIssue]
            return records, has_next
        except CHEMBL_ADAPTER_ERRORS as error:
            handle_error = cast("Callable[[Exception], NoReturn]", self._handle_error)  # pyright: ignore[reportAttributeAccessIssue]
            handle_error(error)

    def _calculate_page_limit(
        self, params: JsonDict, limit: int | None, records_yielded: int
    ) -> int | None:
        """Calculate the limit for the current page request.

        Args:
            params: Current request parameters
            limit: Overall limit for the iteration
            records_yielded: Records already yielded

        Returns:
            Limit for this page request, or None if no more records needed
        """
        if limit is None or "limit" not in params:
            return cast(int | None, params.get("limit"))

        remaining = limit - records_yielded
        if remaining <= 0:
            return None  # Signal to stop iteration

        return min(cast(int, params["limit"]), remaining)

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
            params = self._build_params(offset, entity_type)  # pyright: ignore[reportAttributeAccessIssue]

            page_limit = self._calculate_page_limit(params, limit, records_yielded)
            if page_limit is None:
                break
            if page_limit != params.get("limit"):
                params["limit"] = page_limit

            records, has_next = await self._fetch_page(url, params, entity_type)
            if not records:
                break

            yield records
            records_yielded += len(records)

            # Check if we should continue to next page
            if not has_next or (limit is not None and records_yielded >= limit):
                break
            offset += len(records)


__all__ = ["CHEMBL_ADAPTER_ERRORS", "ChemblFetchPagingMixin"]
