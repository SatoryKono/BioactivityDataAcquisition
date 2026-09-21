"""Real API shape and identity regressions for nested assay parameters."""

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.data_sources.assay_parameters import (
    AssayParametersDataSource,
)


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
