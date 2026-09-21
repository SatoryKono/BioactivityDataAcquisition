"""Expand ChEMBL assay payloads into content-addressed parameter observations."""

from __future__ import annotations

from collections.abc import AsyncIterator

from bioetl.application.core.data_source_mixins import (
    _SourceMetadataDelegationMixin,
    _WrappedDataSourceDelegationMixin,
)
from bioetl.application.core.derived_scan_budget import (
    DEFAULT_SCAN_RECORDS,
    bounded_source_records,
)
from bioetl.application.core.target_data_source_mixins import (
    _TargetEntityFetchDelegationMixin,
)
from bioetl.domain.deterministic_identity import deterministic_uuid
from bioetl.domain.ports import DataSourcePort
from bioetl.domain.types import JsonDict


class AssayParametersDataSource(
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

    TARGET_ENTITY_TYPE = "assay_parameters"

    def __init__(self, data_source: DataSourcePort) -> None:
        self._data_source = data_source

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
        source = self._data_source.fetch(
            entity_type="assay",
            limit=DEFAULT_SCAN_RECORDS + 1,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        emitted = 0
        skip = max(0, offset or 0)
        bounded = bounded_source_records(source)
        try:
            async for assay in bounded:
                for parameter in self._parameters(assay):
                    if skip:
                        skip -= 1
                        continue
                    yield parameter
                    emitted += 1
                    if limit is not None and emitted >= limit:
                        return
        finally:
            await bounded.aclose()

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
