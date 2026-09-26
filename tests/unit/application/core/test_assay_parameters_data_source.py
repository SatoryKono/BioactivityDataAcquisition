"""Real API shape and identity regressions for nested assay parameters."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.data_sources.assay_parameters import (
    AssayParametersDataSource,
)
from bioetl.domain.ports import FilterableDataSourcePort
from bioetl.domain.types import HealthStatus

pytestmark = pytest.mark.unit


class _FilterableAssaySource:
    provider_name = "chembl"

    def __init__(self, assays: list[dict] | None = None) -> None:
        self._assays = assays or []
        self.fetch_calls: list[dict[str, object]] = []
        self.fetch_filtered_calls: list[dict[str, object]] = []
        self.__aenter__ = AsyncMock(return_value=self)
        self.__aexit__ = AsyncMock(return_value=None)
        self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        self.aclose = AsyncMock()

    async def fetch(self, entity_type: str, **kwargs):
        self.fetch_calls.append({"entity_type": entity_type, **kwargs})
        for assay in self._assays:
            yield assay

    async def fetch_filtered(self, entity_type: str, **kwargs):
        self.fetch_filtered_calls.append({"entity_type": entity_type, **kwargs})
        for assay in self._assays:
            yield assay

    async def fetch_multi_filtered(self, entity_type: str, **kwargs):
        for assay in self._assays:
            yield assay

    async def fetch_filtered_with_fallback(self, entity_type: str, **kwargs):
        for assay in self._assays:
            yield assay


@pytest.mark.asyncio
async def test_empty_assays_are_not_emitted_as_malformed_parameters():
    async def records(**kwargs):
        yield {"assay_chembl_id": "CHEMBL615121", "assay_parameters": []}

    adapter = MagicMock()
    adapter.fetch = records
    source = AssayParametersDataSource(adapter)
    assert [row async for row in source.fetch("assay_parameters", limit=1000)] == []


def test_parameter_identity_is_stable_and_parent_scoped():
    parameter = {"type": "PH", "value": 7.4, "units": None}
    first = {"assay_chembl_id": "CHEMBL615121", "assay_parameters": [parameter]}
    reordered = {**first, "assay_parameters": [dict(reversed(list(parameter.items())))]}
    row = AssayParametersDataSource._parameters(first)[0]
    assert row == AssayParametersDataSource._parameters(reordered)[0]
    assert 0 < row["assay_param_id"] < 2**63
    second = {**first, "assay_chembl_id": "CHEMBL615122"}
    assert (
        row["assay_param_id"]
        != AssayParametersDataSource._parameters(second)[0]["assay_param_id"]
    )
    assert row["assay_id"] == "CHEMBL615121"


def test_missing_identity_components_do_not_get_manufactured_keys():
    for assay in (
        {"assay_parameters": [{"type": "PH", "value": 7.4}]},
        {"assay_chembl_id": "CHEMBL615121", "assay_parameters": [{"value": 7.4}]},
        {"assay_chembl_id": "CHEMBL615121"},
    ):
        assert "assay_param_id" not in AssayParametersDataSource._parameters(assay)[0]


@pytest.mark.asyncio
async def test_limit_and_offset_apply_to_parameters_and_close_parent_stream():
    closed = []

    async def records(**kwargs):
        try:
            yield {
                "assay_chembl_id": "CHEMBL615121",
                "assay_parameters": [
                    {"type": "PH", "value": 7},
                    {"type": "PH", "value": 8},
                    {"type": "PH", "value": 9},
                ],
            }
        finally:
            closed.append(True)

    adapter = MagicMock()
    adapter.fetch = records
    source = AssayParametersDataSource(adapter)
    rows = [row async for row in source.fetch("assay_parameters", limit=1, offset=1)]
    assert len(rows) == 1
    assert rows[0]["value"] == 8
    assert closed == [True]


@pytest.mark.asyncio
async def test_assay_parameters_is_filterable_and_scales_upstream_limit():
    assays = [
        {
            "assay_chembl_id": "CHEMBL1",
            "assay_parameters": [{"type": "PH", "value": 7.0}],
        },
        {
            "assay_chembl_id": "CHEMBL2",
            "assay_parameters": [{"type": "PH", "value": 7.4}],
        },
    ]
    adapter = _FilterableAssaySource(assays)
    assert isinstance(adapter, FilterableDataSourcePort)
    source = AssayParametersDataSource(adapter)
    assert isinstance(source, FilterableDataSourcePort)

    rows = [
        row
        async for row in source.fetch_filtered(
            entity_type="assay_parameters",
            filter_ids=["CHEMBL1", "CHEMBL2"],
            filter_field="assay_id",
            limit=1,
        )
    ]
    assert len(rows) == 1
    assert rows[0]["assay_id"] == "CHEMBL1"
    assert adapter.fetch_filtered_calls[-1]["entity_type"] == "assay"
    assert adapter.fetch_filtered_calls[-1]["limit"] == 3


@pytest.mark.asyncio
async def test_assay_parameters_limited_fetch_uses_multiplied_upstream_budget():
    adapter = _FilterableAssaySource(
        [
            {
                "assay_chembl_id": "CHEMBL1",
                "assay_parameters": [{"type": "PH", "value": 7.0}],
            }
        ]
    )
    source = AssayParametersDataSource(adapter)
    _ = [row async for row in source.fetch("assay_parameters", limit=10)]
    assert adapter.fetch_calls[-1]["limit"] == 10 * source.ASSAY_LIMIT_MULTIPLIER + 1
