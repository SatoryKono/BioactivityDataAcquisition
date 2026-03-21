# mypy: disable-error-code=attr-defined
"""Internal filtered-pagination and dedup helpers for ChEMBL fetch paging."""

from __future__ import annotations

__all__ = ["_ChemblFetchPagingFilteredMixin"]

from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator


class _ChemblFetchPagingFilteredMixin:
    """Filtered-page continuation and dedup helpers for ChEMBL paging flow."""

    def _is_duplicate_composite(
        self,
        record: BronzeRecord,
        pk_fields: tuple[str, ...],
        seen_ids: set[str],
        entity_type: str,
        filter_field: str,
    ) -> bool:
        """Check composite-key duplicate, returning True if record should be skipped."""
        composite_key = self._compute_composite_key(record, pk_fields)
        if not composite_key or composite_key == "|".join([""] * len(pk_fields)):
            return False
        if composite_key not in seen_ids:
            seen_ids.add(composite_key)
            return False
        self._logger.debug(
            "skipping_duplicate_record",
            entity_type=entity_type,
            pk_fields=pk_fields,
            composite_key=composite_key,
            filter_field=filter_field,
        )
        self._adapter_metrics.record_dropped_duplicates(entity_type)
        return True

    def _is_duplicate_simple(
        self,
        record: BronzeRecord,
        pk_field: str,
        seen_ids: set[str],
        entity_type: str,
        filter_field: str,
    ) -> bool:
        """Check simple-key duplicate, returning True if record should be skipped."""
        record_id = str(record.get(pk_field, ""))
        if not record_id:
            return False
        if record_id not in seen_ids:
            seen_ids.add(record_id)
            return False
        self._logger.debug(
            "skipping_duplicate_record",
            entity_type=entity_type,
            pk_field=pk_field,
            record_id=record_id,
            filter_field=filter_field,
        )
        self._adapter_metrics.record_dropped_duplicates(entity_type)
        return True

    def _yield_deduplicated(
        self,
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
                if self._is_duplicate_composite(
                    record,
                    pk_fields,
                    seen_ids,
                    entity_type,
                    filter_field,
                ):
                    continue
            elif self._is_duplicate_simple(
                record,
                pk_field,
                seen_ids,
                entity_type,
                filter_field,
            ):
                continue
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
            except self.CHEMBL_ADAPTER_ERRORS:
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
                records,
                seen_ids,
                pk_field,
                entity_type,
                filter_field,
                pk_fields,
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
            records,
            seen_ids,
            pk_field,
            entity_type,
            filter_field,
            pk_fields,
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
