# mypy: disable-error-code=attr-defined
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Multi-field filtered fetch mixin for ChEMBL adapter."""

from __future__ import annotations

__all__ = ["ChemblFetchMultiFilterMixin"]


import itertools
from typing import TYPE_CHECKING

from bioetl.domain.mixin_host import as_mixin_host
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.deduplication import (
    iter_deduplicated_records,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class ChemblFetchMultiFilterMixin:
    """Provides multi-field filter fetch implementation for ChEMBL."""

    async def _fetch_compound_record_intersection(
        self,
        url: str,
        filters: dict[str, list[str]],
        pk_field: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Query one scalar key set and apply the complete AND predicate locally.

        Compound records expose both filter keys as scalar fields. Fetching all
        pages for the smaller key set is a superset of the requested intersection;
        local membership checks preserve that intersection without a Cartesian
        product of remote requests. Other entity/filter shapes retain their
        existing server-side filtering path.
        """
        remote_key = min(filters, key=lambda key: len(filters[key]))
        allowed = {key: frozenset(values) for key, values in filters.items()}
        host = as_mixin_host(self)
        batch_size = host._determine_multi_filter_batch_size(
            url, {remote_key: filters[remote_key]}, "compound_record"
        )
        seen_ids: set[str] = set()
        emitted = 0
        for batch in host._batch_ids(filters[remote_key], batch_size):
            params = host._build_filter_in_params({remote_key: batch})
            async for record in host._fetch_multi_filter_page_loop(
                url, params, "compound_record", pk_field, seen_ids
            ):
                if not all(
                    str(record.get(key)) in values for key, values in allowed.items()
                ):
                    continue
                yield record
                emitted += 1
                if limit is not None and emitted >= limit:
                    return

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
        batch_size: int = as_mixin_host(self)._filter_batch_size  # Any: mixin host
        while batch_size > 1:
            test_filters = {k: v[:batch_size] for k, v in filters.items()}
            test_params = as_mixin_host(self)._build_params(
                0, entity_type
            )  # Any: mixin host
            test_params.update(
                as_mixin_host(self)._build_filter_in_params(test_filters)
            )  # Any: mixin host
            if (
                as_mixin_host(self)._get_projected_url_length(url, test_params) <= 1000
            ):  # Any: mixin host
                break
            batch_size //= 2
            as_mixin_host(self)._logger.info(  # Any: mixin host
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
            params = as_mixin_host(self)._build_params(
                offset, entity_type
            )  # Any: mixin host
            params.update(filter_params)
            records, has_next = await as_mixin_host(self)._fetch_page(
                url, params, entity_type
            )  # Any: mixin host
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
        if not filters or not all(filters.values()):
            return
        if limit is not None and limit <= 0:
            return
        url = as_mixin_host(self)._mapper.get_resource_url(
            entity_type
        )  # Any: mixin host
        pk_field = as_mixin_host(self)._get_api_pk_field(entity_type)  # Any: mixin host
        batch_size = as_mixin_host(self)._determine_multi_filter_batch_size(
            url, filters, entity_type
        )  # Any: mixin host
        filter_keys = list(filters.keys())
        api_filter_keys = [
            as_mixin_host(self)._normalize_filter_field(entity_type, k)
            for k in filter_keys  # Any: mixin host
        ]
        if entity_type == "compound_record" and set(api_filter_keys) == {
            "molecule_chembl_id",
            "document_chembl_id",
        }:
            normalized_filters = dict(
                zip(api_filter_keys, (filters[key] for key in filter_keys), strict=True)
            )
            async for record in self._fetch_compound_record_intersection(
                url, normalized_filters, pk_field, limit
            ):
                yield record
            return
        filter_batches = [
            list(as_mixin_host(self)._batch_ids(filters[k], batch_size))
            for k in filter_keys  # Any: mixin host
        ]
        total_fetched = 0
        seen_ids: set[str] = set()
        for batch_combination in itertools.product(*filter_batches):
            current_filters = dict(zip(api_filter_keys, batch_combination, strict=True))
            filter_params = as_mixin_host(self)._build_filter_in_params(
                current_filters
            )  # Any: mixin host
            async for record in as_mixin_host(
                self
            )._fetch_multi_filter_page_loop(  # Any: mixin host
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
