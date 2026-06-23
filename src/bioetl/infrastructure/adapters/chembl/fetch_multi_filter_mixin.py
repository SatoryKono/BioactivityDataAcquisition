# mypy: disable-error-code=attr-defined
"""Multi-field filtered fetch mixin for ChEMBL adapter."""

from __future__ import annotations

__all__ = ["ChemblFetchMultiFilterMixin"]


import itertools
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.deduplication import (
    iter_deduplicated_records,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class ChemblFetchMultiFilterMixin:
    """Provides multi-field filter fetch implementation for ChEMBL."""

    def _determine_multi_filter_batch_size(
        self,
        url: str,
        filters: dict[str, list[str]],
        entity_type: str,
    ) -> int:
        """Halve batch_size until projected URL fits the 1000-char limit.

        Args:
            url: Base API resource URL used to estimate total request length.
            filters: Mapping of API field names to lists of filter values.
            entity_type: ChEMBL entity type (e.g., ``"activity"``).

        Returns:
            Maximum batch size that keeps the URL within the 1000-character limit.
        """
        batch_size: int = self._filter_batch_size
        while batch_size > 1:
            test_filters = {k: v[:batch_size] for k, v in filters.items()}
            test_params = self._build_params(0, entity_type)
            test_params.update(self._build_filter_in_params(test_filters))
            if self._get_projected_url_length(url, test_params) <= 1000:
                break
            batch_size //= 2
            self._logger.info(
                "reducing_multi_filter_batch_size",
                entity_type=entity_type,
                new_batch_size=batch_size,
                reason="url_length_limit_exceeded",
            )
        return batch_size

    async def _fetch_multi_filter_page_loop(
        self,
        url: str,
        filter_params: dict[str, str],
        entity_type: str,
        pk_field: str,
        seen_ids: set[str],
    ) -> AsyncIterator[BronzeRecord]:
        """Paginate through a single filter combination, deduplicating records."""
        offset = 0
        logger = getattr(self, "_logger", None)
        metrics = getattr(self, "_adapter_metrics", None)
        while True:
            params = self._build_params(offset, entity_type)
            params.update(filter_params)
            records, has_next = await self._fetch_page(url, params, entity_type)
            if not records:
                break
            for record in iter_deduplicated_records(
                records,
                seen_keys=seen_ids,
                primary_field=pk_field,
                entity_type=entity_type,
                logger=logger,
                metrics=metrics,
            ):
                yield record
            if not has_next:
                break
            offset += len(records)

    async def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch ChEMBL data with AND-logic multi-field filtering and batching.

        Args:
            entity_type: ChEMBL entity type (e.g., ``"activity"``).
            filters: Mapping of API field names to lists of allowed values;
                all conditions are combined with AND logic.
            limit: Maximum number of records to yield, or None for no limit.

        Returns:
            Async iterator of deduplicated BronzeRecord dicts matching all filters.
        """
        if not filters:
            return
        url = self._mapper.get_resource_url(entity_type)
        pk_field = self._get_api_pk_field(entity_type)
        batch_size = self._determine_multi_filter_batch_size(url, filters, entity_type)
        filter_keys = list(filters.keys())
        api_filter_keys = [
            self._normalize_filter_field(entity_type, k) for k in filter_keys
        ]
        filter_batches = [
            list(self._batch_ids(filters[k], batch_size)) for k in filter_keys
        ]
        total_fetched = 0
        seen_ids: set[str] = set()
        for batch_combination in itertools.product(*filter_batches):
            current_filters = dict(zip(api_filter_keys, batch_combination, strict=True))
            filter_params = self._build_filter_in_params(current_filters)
            async for record in self._fetch_multi_filter_page_loop(
                url,
                filter_params,
                entity_type,
                pk_field,
                seen_ids,
            ):
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return
