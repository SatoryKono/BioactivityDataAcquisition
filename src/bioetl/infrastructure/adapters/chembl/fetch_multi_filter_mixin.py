"""Multi-field filtered fetch mixin for ChEMBL adapter."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.chembl.entity_mapper import ChemblEntityMapper


class ChemblFetchMultiFilterMixin:
    """Provides multi-field filter fetch implementation for ChEMBL."""

    logger: LoggerPort
    _mapper: ChemblEntityMapper
    _filter_batch_size: int
    _build_params: Callable[[int, str | None], dict[str, str | int | bool]]
    _build_filter_in_params: Callable[[dict[str, list[str]]], dict[str, str]]
    _get_projected_url_length: Callable[[str, dict[str, str | int | bool]], int]
    _get_api_pk_field: Callable[[str], str]
    _normalize_filter_field: Callable[[str, str], str]
    _batch_ids: Callable[[list[str], int], Iterator[list[str]]]
    _fetch_page: Callable[
        [str, dict[str, str | int | bool], str],
        Awaitable[tuple[list[BronzeRecord], bool]],
    ]
    _is_duplicate_record: Callable[[BronzeRecord, str, set[str], str], bool]

    def _determine_multi_filter_batch_size(
        self: ChemblFetchMultiFilterMixin,
        url: str,
        filters: dict[str, list[str]],
        entity_type: str,
    ) -> int:
        """Halve batch_size until projected URL fits the 1000-char limit."""
        batch_size: int = self._filter_batch_size
        while batch_size > 1:
            test_filters = {k: v[:batch_size] for k, v in filters.items()}
            test_params = self._build_params(0, entity_type)
            test_params.update(self._build_filter_in_params(test_filters))
            if self._get_projected_url_length(url, test_params) <= 1000:
                break
            batch_size //= 2
            self.logger.info(
                "reducing_multi_filter_batch_size",
                entity_type=entity_type,
                new_batch_size=batch_size,
                reason="url_length_limit_exceeded",
            )
        return batch_size

    async def fetch_multi_filtered(
        self: ChemblFetchMultiFilterMixin,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records from ChEMBL with multiple filter fields (AND logic).

        Implements FilterableDataSourcePort.fetch_multi_filtered().

        Makes requests with multiple __in parameters, e.g.:
        ?molecule_chembl_id__in=CHEMBL25,CHEMBL26&document_chembl_id__in=CHEMBL1123

        ChEMBL API returns records matching ALL filter conditions (AND logic).
        Supports automatic batching and URL length validation (1000 char limit).

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

        url = self._mapper.get_resource_url(entity_type)
        pk_field = self._get_api_pk_field(entity_type)
        batch_size = self._determine_multi_filter_batch_size(url, filters, entity_type)

        # Prepare batches for each filter field
        filter_keys = list(filters.keys())
        api_filter_keys = [
            self._normalize_filter_field(entity_type, k) for k in filter_keys
        ]
        filter_batches = [
            list(self._batch_ids(filters[k], batch_size)) for k in filter_keys
        ]

        total_fetched = 0
        seen_ids: set[str] = set()

        # Iterate over cartesian product of batches to cover all combinations
        # ChEMBL API returns records matching ALL filters in the request (AND logic)
        for batch_combination in itertools.product(*filter_batches):
            current_filters = dict(zip(api_filter_keys, batch_combination, strict=True))
            filter_params = self._build_filter_in_params(current_filters)

            offset = 0
            while True:
                params = self._build_params(offset, entity_type)
                params.update(filter_params)

                records, has_next = await self._fetch_page(url, params, entity_type)
                if not records:
                    break

                for record in records:
                    if self._is_duplicate_record(
                        record, pk_field, seen_ids, entity_type
                    ):
                        continue
                    yield record
                    total_fetched += 1
                    if limit and total_fetched >= limit:
                        return

                if not has_next:
                    break
                offset += len(records)
