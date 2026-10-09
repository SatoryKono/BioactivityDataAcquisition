"""Subcellular Fraction Data Source wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from bioetl.application.core import subcellular_fraction_support as support
from bioetl.application.core.data_sources._derived_assay_source import (
    _DerivedAssayDataSourceBase,
)
from bioetl.application.core.derived_scan_budget import iter_derived_source
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort

__all__ = ["SubcellularFractionDataSource"]


class SubcellularFractionDataSource(_DerivedAssayDataSourceBase):
    """Wraps a DataSourcePort to extract subcellular fraction records."""

    TARGET_ENTITY_TYPE = "subcellular_fraction"
    # assay_subcellular_fraction is sparse; scale upstream assays for --limit runs.
    ASSAY_LIMIT_MULTIPLIER: ClassVar[int] = 200

    def __init__(self, data_source: DataSourcePort) -> None:
        super().__init__(data_source)
        self._seen_fractions: set[str] = set()

    def _after_wrapped_data_source_enter(self) -> None:
        self._seen_fractions = set()

    async def _fetch_target_records(
        self,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        skip = max(0, offset or 0)
        seen = 0
        emitted = 0
        fetch_limit = None if limit is None else (limit + skip)
        async for record in self._fetch_subcellular_fractions(
            fetch_limit, query, filter_ids, filter_field
        ):
            if seen < skip:
                seen += 1
                continue
            yield record
            emitted += 1
            if limit is not None and emitted >= limit:
                return

    async def _fetch_subcellular_fractions(
        self,
        limit: int | None,
        query: str | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
    ) -> AsyncIterator[JsonDict]:
        assays = self._iter_assays(
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        async for record in self._extract_unique_fractions(
            assays,
            limit,
        ):
            yield record

    @staticmethod
    def _normalize_fraction(
        raw_fraction: Any,  # Any: upstream assay payload may carry heterogeneous scalar/object values.
    ) -> str | None:
        return support.normalize_fraction(raw_fraction)

    @staticmethod
    def _compute_entity_id(subcellular_fraction: str) -> str:
        return support.compute_entity_id(subcellular_fraction)

    def _create_fraction_record(
        self,
        assay: JsonDict,
        fraction: str,
    ) -> JsonDict:
        return support.create_fraction_record(assay, fraction)

    def _iter_derived_records(
        self,
        assays: AsyncIterator[JsonDict],
        *,
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        return self._fetch_filtered_fractions(assays, limit)

    def _yield_target_records_from_fallback_source_records(
        self,
        source_records: AsyncIterator[
            object
        ],  # object: fallback source stream forwards raw upstream records before normalization.
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        scan_limit = self._upstream_limit(limit)
        return self._fetch_filtered_fractions(
            iter_derived_source(
                source_records,
                output_limit=limit,
                scan_limit=scan_limit,
            ),
            limit,
        )

    async def _fetch_filtered_fractions(
        self,
        assays: AsyncIterator[object],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        async for record in self._extract_unique_fractions(
            self._coerce_assay_records(assays), limit
        ):
            yield record

    async def _extract_unique_fractions(
        self,
        assays: AsyncIterator[JsonDict],
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        async for record in support.extract_unique_fraction_records(
            assays,
            limit,
            self._seen_fractions,
            # Limited runs stop once the unique quota is filled so upstream I/O
            # stays inside the derived-scan time budget. Unlimited runs keep the
            # full-stream aggregation contract (#7787).
            continue_after_limit=limit is None,
        ):
            yield record
