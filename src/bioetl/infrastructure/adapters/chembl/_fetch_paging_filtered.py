# mypy: disable-error-code=attr-defined
# Host attrs/methods provided by concrete composition.
"""Internal filtered-pagination and dedup helpers for ChEMBL fetch paging."""

from __future__ import annotations

__all__ = ["_ChemblFetchPagingFilteredMixin"]

from typing import TYPE_CHECKING

from bioetl.domain.mixin_host import as_mixin_host
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.deduplication import (
    iter_deduplicated_records,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator


class _ChemblFetchPagingFilteredMixin:
    """Filtered-page continuation and dedup helpers for ChEMBL paging flow."""

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
        composite_fields = (
            pk_fields if pk_fields is not None and len(pk_fields) > 1 else None
        )
        logger = getattr(self, "_logger", None)
        metrics = getattr(self, "_adapter_metrics", None)
        yield from iter_deduplicated_records(
            records,
            seen_keys=seen_ids,
            primary_field=(
                composite_fields[0] if composite_fields is not None else pk_field
            ),
            composite_fields=composite_fields,
            composite_key_builder=(
                as_mixin_host(self)._compute_composite_key
                if composite_fields is not None
                else None  # Any: mixin host
            ),
            entity_type=entity_type,
            logger=logger,
            metrics=metrics,
            log_context={"filter_field": filter_field},
        )

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
            params = as_mixin_host(self)._build_params(
                offset, entity_type
            )  # Any: mixin host
            params.update(
                as_mixin_host(self)._build_filter_params(
                    entity_type, filter_field, id_batch
                )  # Any: mixin host
            )
            try:
                records, has_next = await as_mixin_host(self)._fetch_page(
                    url, params, entity_type
                )  # Any: mixin host
            except as_mixin_host(self).CHEMBL_ADAPTER_ERRORS:  # Any: mixin host
                as_mixin_host(self)._logger.warning(  # Any: mixin host
                    "chembl_pagination_interrupted",
                    entity_type=entity_type,
                    offset=offset,
                    records_yielded=len(seen_ids),
                )
                return
            if not records:
                break
            for record in as_mixin_host(self)._yield_deduplicated(  # Any: mixin host
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
        url = as_mixin_host(self)._mapper.get_resource_url(
            entity_type
        )  # Any: mixin host
        seen_ids: set[str] = set()
        pk_field = as_mixin_host(self)._get_api_pk_field(entity_type)  # Any: mixin host
        pk_fields = as_mixin_host(self)._get_api_dedup_fields(
            entity_type
        )  # Any: mixin host

        api_filter_field = as_mixin_host(self)._normalize_filter_field(
            entity_type, filter_field
        )  # Any: mixin host
        skip_pagination = (
            len(pk_fields) == 1
            and pk_fields[0] == api_filter_field
            and len(id_batch) <= as_mixin_host(self)._page_size  # Any: mixin host
        )

        params = as_mixin_host(self)._build_params(0, entity_type)  # Any: mixin host
        if skip_pagination:
            params.pop("limit", None)
            params.pop("offset", None)
        params.update(
            as_mixin_host(self)._build_filter_params(
                entity_type, filter_field, id_batch
            )
        )  # Any: mixin host

        records, has_next = await as_mixin_host(self)._fetch_page(
            url, params, entity_type
        )  # Any: mixin host
        if not records:
            return

        for record in as_mixin_host(self)._yield_deduplicated(  # Any: mixin host
            records,
            seen_ids,
            pk_field,
            entity_type,
            filter_field,
            pk_fields,
        ):
            yield record

        if has_next:
            async for record in as_mixin_host(
                self
            )._paginate_filter_results(  # Any: mixin host
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
