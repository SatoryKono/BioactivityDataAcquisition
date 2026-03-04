"""Adapter mixin orchestrating ChEMBL fetch flows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.chembl.fetch_multi_filter_mixin import (
    ChemblFetchMultiFilterMixin,
)
from bioetl.infrastructure.adapters.chembl.fetch_paging_mixin import (
    ChemblFetchPagingMixin,
)
from bioetl.infrastructure.adapters.chembl.fetch_resilience_mixin import (
    ChemblFetchResilienceMixin,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class ChemblFetchAdapterMixin(
    ChemblFetchResilienceMixin,
    ChemblFetchPagingMixin,
    ChemblFetchMultiFilterMixin,
):
    """Provides ChEMBL pagination, filtering, and retry fetch flows."""

    async def _fetch_filtered(
        self: Any,  # Any: mixin self type
        entity_type: str,
        limit: int | None,
        filter_ids: list[str],
        filter_field: str,
    ) -> AsyncIterator[BronzeRecord]:
        """Perform filtered fetch using ID batches with client-side deduplication."""
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
        """Fetch records from ChEMBL."""
        _ = query

        if filter_ids and filter_field:
            async for record in self._fetch_filtered(
                entity_type, limit, filter_ids, filter_field
            ):
                yield record
            return

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
        """Fetch with fallback (ChEMBL IDs always resolvable, fallback ignored)."""
        _ = fallback_mapping
        async for record in self._fetch_filtered(
            entity_type, limit, filter_ids, filter_field
        ):
            yield record


__all__ = ["ChemblFetchAdapterMixin"]
