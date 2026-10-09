"""Expand ChEMBL assay payloads into content-addressed parameter observations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, ClassVar, cast

from bioetl.application.core.data_source_mixins import (
    _SourceMetadataDelegationMixin,
    _WrappedDataSourceDelegationMixin,
)
from bioetl.application.core.derived_scan_budget import (
    iter_derived_source,
    resolve_derived_upstream_limit,
)
from bioetl.application.core.target_data_source_mixins import (
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
)
from bioetl.domain.deterministic_identity import deterministic_uuid
from bioetl.domain.ports import DataSourcePort
from bioetl.domain.types import JsonDict


class AssayParametersDataSource(
    _FallbackFilterableTargetFetchMixin,
    _FilterableTargetDelegationMixin,
    _TargetEntityFetchDelegationMixin,
    _WrappedDataSourceDelegationMixin,
    _SourceMetadataDelegationMixin,
):
    """Expose the API's nested parameters, never entire assays as parameters.

    The public API has no parameter surrogate key. Its v1 local identity is a
    positive signed-64-bit UUID-derived content key over assay ID and parameter
    payload. An identical repeated observation is the same record; changing a
    parameter value creates a new observation. It is not a ChEMBL database PK.
    """

    SOURCE_ENTITY_TYPE = "assay"
    TARGET_ENTITY_TYPE = "assay_parameters"
    # Nested parameters are sparse; scale upstream assays for limited runs.
    ASSAY_LIMIT_MULTIPLIER: ClassVar[int] = 20

    def __init__(self, data_source: DataSourcePort) -> None:
        self._data_source = data_source

    def _upstream_limit(
        self,
        limit: int | None,
        filter_ids: list[str] | None = None,
    ) -> int:
        return resolve_derived_upstream_limit(
            limit,
            multiplier=self.ASSAY_LIMIT_MULTIPLIER,
            filter_ids=filter_ids,
        )

    async def _fetch_target_records(
        self,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        if limit is not None and limit <= 0:
            return
        scan_limit = self._upstream_limit(limit, filter_ids)
        source = self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=scan_limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        async for parameter in self._expand_parameters(
            iter_derived_source(source, output_limit=limit, scan_limit=scan_limit),
            limit=limit,
            offset=offset,
        ):
            yield parameter

    async def _fetch_target_filtered_records(
        self,
        filterable: Any,  # Any: mixin provides a duck-typed filtered fetch surface.
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        scan_limit = self._upstream_limit(limit, filter_ids)
        async for parameter in self._expand_parameters(
            iter_derived_source(
                filterable.fetch_filtered(
                    entity_type=self.SOURCE_ENTITY_TYPE,
                    filter_ids=filter_ids,
                    filter_field=filter_field,
                    limit=scan_limit,
                ),
                output_limit=limit,
                scan_limit=scan_limit,
            ),
            limit=limit,
        ):
            yield parameter

    async def _fetch_target_multi_filtered_records(
        self,
        filterable: Any,  # Any: mixin accepts multiple runtime filterable adapters.
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        id_count = sum(len(values) for values in filters.values())
        scan_limit = resolve_derived_upstream_limit(
            limit,
            multiplier=self.ASSAY_LIMIT_MULTIPLIER,
            filter_id_count=id_count,
        )
        async for parameter in self._expand_parameters(
            iter_derived_source(
                filterable.fetch_multi_filtered(
                    entity_type=self.SOURCE_ENTITY_TYPE,
                    filters=filters,
                    limit=scan_limit,
                ),
                output_limit=limit,
                scan_limit=scan_limit,
            ),
            limit=limit,
        ):
            yield parameter

    def _resolve_target_fallback_upstream_limit(
        self,
        limit: int | None = None,
    ) -> int | None:
        return self._upstream_limit(limit)

    def _yield_target_records_from_fallback_source_records(
        self,
        source_records: AsyncIterator[
            object
        ],  # object: fallback source stream forwards raw upstream records.
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        return self._expand_parameters(
            self._coerce_assay_records(source_records),
            limit=limit,
        )

    async def _coerce_assay_records(
        self,
        assays: AsyncIterator[object],
    ) -> AsyncIterator[JsonDict]:
        async for assay in assays:
            if isinstance(assay, dict):
                yield cast("JsonDict", assay)

    async def _expand_parameters(
        self,
        assays: AsyncIterator[JsonDict],
        *,
        limit: int | None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        emitted = 0
        skip = max(0, offset or 0)
        try:
            async for assay in assays:
                for parameter in self._parameters(assay):
                    if skip:
                        skip -= 1
                        continue
                    yield parameter
                    emitted += 1
                    if limit is not None and emitted >= limit:
                        return
        finally:
            close = getattr(assays, "aclose", None)
            if close is not None:
                await close()

    @staticmethod
    def _parameters(assay: JsonDict) -> list[JsonDict]:
        values = assay.get("assay_parameters")
        # Missing/malformed payloads must reach ordinary record quarantine.
        if not isinstance(values, list):
            return [dict(assay)]
        result: list[JsonDict] = []
        assay_id = assay.get("assay_chembl_id") or assay.get("assay_id")
        for value in values:
            if not isinstance(value, dict):
                result.append({"assay_id": assay_id, "invalid_parameter": value})
                continue
            row = {**value, "assay_id": assay_id}
            if assay_id and value.get("type") and row.get("assay_param_id") is None:
                identity = deterministic_uuid(
                    "chembl.assay_parameter.observation.v1", row
                ).int
                row["assay_param_id"] = (identity & ((1 << 63) - 1)) or 1
            result.append(row)
        return result
