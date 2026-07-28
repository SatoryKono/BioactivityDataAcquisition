# mypy: disable-error-code=attr-defined
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
# pyright: reportInvalidCast=false
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Adapter mixin orchestrating ChEMBL fetch flows."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

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
from bioetl.infrastructure.adapters.common.deduplication import (
    iter_deduplicated_records,
)
from bioetl.infrastructure.adapters.common.fetch_resilience_template import (
    FilteredBatchRecoveryHost,
    iter_deduplicated_filtered_id_batches,
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
        self,
        entity_type: str,
        limit: int | None,
        filter_ids: list[str],
        filter_field: str,
    ) -> AsyncIterator[BronzeRecord]:
        """Perform filtered fetch using ID batches with client-side deduplication.

        Args:
            entity_type: ChEMBL entity type (e.g., ``"activity"``).
            limit: Maximum number of records to yield, or None for no limit.
            filter_ids: List of IDs to filter by in the API query.
            filter_field: API field name to apply the ID filter on.

        Returns:
            Async iterator of deduplicated BronzeRecord dicts.
        """
        host = cast(FilteredBatchRecoveryHost, self)
        async for record in iter_deduplicated_filtered_id_batches(
            host,
            entity_type=entity_type,
            limit=limit,
            filter_ids=filter_ids,
            filter_field=filter_field,
            batch_size=self._filter_batch_size,
        ):
            yield record

    async def _fetch_standard(
        self,
        entity_type: str,
        limit: int | None,
        offset: int = 0,
    ) -> AsyncIterator[BronzeRecord]:
        """Perform standard paginated fetch with client-side deduplication.

        Args:
            entity_type: ChEMBL entity type (e.g., ``"activity"``).
            limit: Maximum number of records to yield, or None for no limit.
            offset: Starting offset for pagination (default 0).

        Returns:
            Async iterator of deduplicated BronzeRecord dicts.
        """
        total_fetched = 0
        seen_keys: set[str] = set()
        pk_field = self._get_api_pk_field(entity_type)
        pk_fields = self._get_api_dedup_fields(entity_type)
        logger = getattr(self, "_logger", None)
        metrics = getattr(self, "_adapter_metrics", None)

        async for records in self._page_iterator(
            entity_type, limit, start_offset=offset
        ):
            for record in iter_deduplicated_records(
                records,
                seen_keys=seen_keys,
                primary_field=pk_field,
                composite_fields=pk_fields if len(pk_fields) > 1 else None,
                composite_key_builder=self._compute_composite_key,
                entity_type=entity_type,
                logger=logger,
                metrics=metrics,
            ):
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records from ChEMBL.

        Args:
            entity_type: ChEMBL entity type (e.g., ``"activity"``).
            limit: Maximum number of records to yield, or None for no limit.
            query: Free-text query string (ignored by ChEMBL adapter).
            filter_ids: List of IDs for filtered fetch, or None for all records.
            filter_field: API field to apply the ID filter on; required when
                filter_ids is provided.
            offset: Starting pagination offset, or None to start from 0.

        Returns:
            Async iterator of BronzeRecord dicts.
        """
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
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records from ChEMBL with ID filtering.

        Implements FilterableDataSourcePort.fetch_filtered().

        Args:
            entity_type: ChEMBL entity type (e.g., ``"activity"``).
            filter_ids: List of IDs to filter by.
            filter_field: API field name to apply the ID filter on.
            limit: Maximum number of records to yield, or None for no limit.

        Returns:
            Async iterator of filtered BronzeRecord dicts.
        """
        async for record in self._fetch_filtered(
            entity_type, limit, filter_ids, filter_field
        ):
            yield record

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch with fallback (ChEMBL IDs always resolvable, fallback ignored).

        Args:
            entity_type: ChEMBL entity type (e.g., ``"activity"``).
            filter_ids: List of IDs to filter by.
            filter_field: API field name to apply the ID filter on.
            fallback_mapping: Mapping of alternative lookup keys to IDs;
                ignored for ChEMBL as all IDs are directly resolvable.
            limit: Maximum number of records to yield, or None for no limit.

        Returns:
            Async iterator of filtered BronzeRecord dicts.
        """
        _ = fallback_mapping
        async for record in self._fetch_filtered(
            entity_type, limit, filter_ids, filter_field
        ):
            yield record


__all__ = ["ChemblFetchAdapterMixin"]
