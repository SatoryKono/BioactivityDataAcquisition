# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""E2E tests for ChEMBL Molecule pipeline.

Tests the complete pipeline execution from fetch to Gold layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/chembl/
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pandas as pd
import pytest
import zstandard as zstd

from bioetl.composition.bootstrap import bootstrap_pipeline_runner
from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
from bioetl.domain.contracts.gold import ChEMBLMoleculeGoldSchema
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

from .conftest import (
    _clear_runtime_config_caches,
    create_test_context,
    get_gold_records,
    get_silver_records,
)
from tests.helpers.e2e_schema_assertions import assert_records_have_required_fields

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.asyncio,
    pytest.mark.usefixtures("strict_dq_env"),
]

_SCD_COLUMNS = {"_valid_from", "_valid_to", "_is_current", "_version"}


@pytest.fixture
def molecule_sample() -> dict:
    path = Path(__file__).parents[1] / "fixtures/chembl_molecule_phase_records.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def molecule_cache(e2e_data_dir: Path, molecule_sample: dict, monkeypatch) -> Path:
    """Use recorded public fields and the production SCD2/strict DQ path."""
    monkeypatch.setenv("BIOETL_TEST_MODE", "false")
    monkeypatch.setenv("BIOETL_REPORT_ROOT", str(e2e_data_dir / "run-reports"))
    monkeypatch.setenv("BIOETL_ARCHIVE_ROOT", str(e2e_data_dir / "archive"))
    monkeypatch.setenv("BIOETL_ENFORCE_REPORT_ROOT_MARKER", "false")
    monkeypatch.setattr(
        httpx.AsyncClient,
        "request",
        AsyncMock(side_effect=AssertionError("Cached Molecule E2E attempted HTTP")),
    )
    _clear_runtime_config_caches()
    root = e2e_data_dir / "cached-input"
    date_root = root / "2026-11-18"
    date_root.mkdir(parents=True)
    batch_id = deterministic_uuid_from_callsite("molecule_phase_fixture")
    payload = (
        b"\n".join(
            json.dumps(record, sort_keys=True).encode()
            for record in molecule_sample["records"]
        )
        + b"\n"
    )
    (date_root / f"batch_2026-11-18_{batch_id}.jsonl.zst").write_bytes(
        zstd.ZstdCompressor().compress(payload)
    )
    return root


def _cached_context(path: Path) -> PipelineRunContext:
    return replace(
        create_test_context("chembl_molecule", limit=2),
        cached_bronze=CachedBronzeContext.from_options(
            path=str(path), date="2026-11-18"
        ),
    )


def _assert_gold_contract(records: list[dict]) -> None:
    schema = ChEMBLMoleculeGoldSchema.to_schema()
    assert schema.strict is True
    assert set(records[0]) <= set(schema.columns) | _SCD_COLUMNS
    frame = pd.DataFrame.from_records(records).drop(columns=list(_SCD_COLUMNS))
    ChEMBLMoleculeGoldSchema.validate(frame, lazy=True)


async def test_chembl_molecule_full_cycle(
    e2e_data_dir: Path, molecule_cache: Path, molecule_sample: dict
) -> None:
    """Recorded decimal phases reach strict Silver and actual SCD2 Gold."""
    await bootstrap_pipeline_runner(_cached_context(molecule_cache)).run()
    records = await get_silver_records(e2e_data_dir, "chembl_molecule")
    gold = await get_gold_records(e2e_data_dir, "chembl_molecule")
    expected = molecule_sample["expected_phases"]
    assert len(records) == len(gold) == len(expected)
    assert {row["molecule_id"]: row["max_phase"] for row in records} == expected
    assert {row["molecule_id"]: row["max_phase"] for row in gold} == expected
    assert {row["molecule_id"]: row["entity_id"] for row in records} == {
        row["molecule_id"]: row["entity_id"] for row in gold
    }
    assert all(row["_is_current"] for row in gold)
    _assert_gold_contract(gold)
    assert_records_have_required_fields(
        records,
        ("molecule_id",),
        entity_label="chembl_molecule.silver",
    )


async def test_chembl_molecule_structural_fields(
    e2e_data_dir: Path, molecule_cache: Path, molecule_sample: dict
) -> None:
    """The production transformation preserves the recorded structure anchors."""
    await bootstrap_pipeline_runner(_cached_context(molecule_cache)).run()
    records = await get_silver_records(e2e_data_dir, "chembl_molecule")
    assert_records_have_required_fields(
        records,
        ("molecule_id",),
        entity_label="chembl_molecule.structural",
    )
    expected = {
        row["molecule_chembl_id"]: row["molecule_structures"]
        for row in molecule_sample["records"]
    }
    assert len(records) == len(expected)
    for row in records:
        structure = expected[row["molecule_id"]]
        assert row["canonical_smiles"] == structure["canonical_smiles"]
        assert row["inchi_key"] == structure["standard_inchi_key"]


async def test_chembl_molecule_identical_cached_run_is_scd2_idempotent(
    e2e_data_dir: Path, molecule_cache: Path, molecule_sample: dict
) -> None:
    await bootstrap_pipeline_runner(_cached_context(molecule_cache)).run()
    before = await get_gold_records(e2e_data_dir, "chembl_molecule")
    await bootstrap_pipeline_runner(_cached_context(molecule_cache)).run()
    after = await get_gold_records(e2e_data_dir, "chembl_molecule")
    assert len(before) == len(after) == len(molecule_sample["records"])
    assert all(row["_is_current"] for row in after)
    fields = ("entity_id", "content_hash", "max_phase", "_version", "_valid_from")
    assert {row["molecule_id"]: tuple(row[k] for k in fields) for row in before} == {
        row["molecule_id"]: tuple(row[k] for k in fields) for row in after
    }
