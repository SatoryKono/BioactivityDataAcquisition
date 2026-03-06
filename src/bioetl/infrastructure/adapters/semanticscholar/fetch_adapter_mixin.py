# mypy: disable-error-code=attr-defined
"""Fetch and fallback entrypoints for SemanticScholarAdapter.

Contains FilterableDataSourcePort-compatible filtering methods.
"""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, cast

from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class SemanticScholarFetchAdapterMixin:
    """Public fetch/filter/fallback paths extracted from adapter facade."""

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records via search endpoint or delegated filtered path."""
        del offset
        if filter_ids:
            async for record in self._fetch_from_filter_ids(
                entity_type=entity_type,
                filter_ids=filter_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                yield record
            return

        self._validate_entity_type(entity_type)
        current_offset = 0
        page_size = min(100, limit or 100)
        fetched = 0
        while True:
            records, next_offset = await self._fetch_search_page(
                query=query,
                page_size=page_size,
                current_offset=current_offset,
            )
            for record in records:
                if limit and fetched >= limit:
                    return
                yield record
                fetched += 1
            if next_offset is None or (limit and fetched >= limit):
                return
            current_offset = next_offset

    async def _fetch_from_filter_ids(
        self,
        *,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Delegate filtered fetch path."""
        effective_filter_field = filter_field or "doi"
        async for record in self.fetch_filtered(
            entity_type=entity_type,
            filter_ids=filter_ids,
            filter_field=effective_filter_field,
            limit=limit,
        ):
            yield record

    @staticmethod
    def _validate_entity_type(entity_type: str) -> None:
        """Validate supported Semantic Scholar entity types."""
        if entity_type in ("publication", "paper"):
            return
        raise ValueError(
            "SemanticScholarAdapter supports 'publication' or 'paper', "
            f"got: {entity_type}"
        )

    async def _fetch_search_page(
        self,
        *,
        query: str | None,
        page_size: int,
        current_offset: int,
    ) -> tuple[list[BronzeRecord], int | None]:
        """Fetch one search page and emit request telemetry.

        Returns:
            Tuple of (list of publication records for the page, next offset integer or None if last page).
        """
        params: JsonDict = {
            "query": query or "*",
            "fields": self.fields,
            "offset": current_offset,
            "limit": page_size,
        }
        url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/search"
        start_time = time.perf_counter()
        with self._adapter_metrics.measure_request("/paper/search"):
            response = await self.http_client.get_once(
                url, params=params, headers=self._build_headers()
            )
        duration_ms = (time.perf_counter() - start_time) * 1000
        with contextlib.suppress(Exception):
            self._request_collector.record_from_response(response, duration_ms)
        data = response.json()
        return list(data.get("data", [])), data.get("next")

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Batch DOI resolution via POST /paper/batch."""
        del entity_type
        if filter_field != "doi":
            self.logger.warning(
                "unsupported_filter_field",
                field=filter_field,
                expected="doi",
            )

        dois = filter_ids[:limit] if limit else filter_ids
        fetched = 0
        for idx in range(0, len(dois), self.batch_size):
            batch = dois[idx: idx + self.batch_size]
            async for record in self._fetch_by_dois(batch):
                record["_lookup_method"] = "doi"
                yield record
                fetched += 1
                if limit and fetched >= limit:
                    return

    async def _batch_doi_phase(
        self,
        valid_dois: list[str],
        resolved_dois: set[str],
        limit: int | None,
        start_count: int,
    ) -> AsyncIterator[BronzeRecord]:
        """Phase-1 DOI resolution preserving unresolved markers."""
        count = start_count
        for idx in range(0, len(valid_dois), self.batch_size):
            if limit and count >= limit:
                return

            batch = valid_dois[idx: idx + self.batch_size]
            batch_results = await self._fetch_batch_with_nulls(batch)
            for doi, record in zip(batch, batch_results, strict=True):
                if record is None:
                    continue
                resolved_dois.add(doi.lower())
                record["_lookup_method"] = "doi"
                record["_resolved_doi"] = doi
                count += 1
                yield record
                if limit and count >= limit:
                    return

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch by DOI and recover unresolved records through title fallback."""
        del entity_type
        resolved_dois: set[str] = set()

        def _primary_records(
            primary_ids: list[str], request_limit: int | None
        ) -> AsyncIterator[BronzeRecord]:
            return self._batch_doi_phase(primary_ids, resolved_dois, request_limit, 0)

        def _extract_record_doi(record: BronzeRecord) -> str | None:
            resolved = record.pop("_resolved_doi", None)
            if isinstance(resolved, str) and resolved.strip():
                return cast("str | None", self._normalize_doi(resolved))
            return None

        async for record in self._fallback_decorator.execute(
            filter_ids=filter_ids,
            fallback_mapping=fallback_mapping,
            primary_record_fetcher=_primary_records,
            limit=limit,
            filter_field=filter_field,
            extract_record_id=_extract_record_doi,
        ):
            yield record

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Semantic Scholar does not support multi-field filtering."""
        del entity_type, filters, limit
        raise NotImplementedError(
            "Semantic Scholar adapter supports only DOI filtering. "
            "Use fetch_filtered() or fetch_filtered_with_fallback()."
        )
        yield {}
