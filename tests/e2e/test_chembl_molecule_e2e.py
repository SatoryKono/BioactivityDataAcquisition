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

Tests production transformation, strict Gold writes and SCD2 with recorded
public Bronze fields. HTTP is forbidden; live extraction has separate tests.
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
from bioetl.infrastructure.storage.gold.writer_schema_helpers import (
    _project_records_for_gold_schema,
)
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

from .conftest import (
    _clear_runtime_config_caches,
    _read_delta_records,
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
_OCCURRENCE_COLUMNS = {"_dq_warn", "_dq_error", "_index"}


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
    expected_columns = (set(schema.columns) - _OCCURRENCE_COLUMNS) | _SCD_COLUMNS
    assert all(set(record) == expected_columns for record in records)
    # The writer validates the complete contract, then omits occurrence fields
    # from persisted Gold. Reuse its canonical projection for read-back checks.
    business = [
        {key: value for key, value in record.items() if key not in _SCD_COLUMNS}
        for record in records
    ]
    projected = _project_records_for_gold_schema(business, schema=schema)
    frame = pd.DataFrame.from_records(projected)
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


@pytest.mark.parametrize("invalid_phase", [1.5, 4.9])
async def test_invalid_phase_is_quarantined_without_contaminating_gold(
    e2e_data_dir: Path,
    molecule_cache: Path,
    molecule_sample: dict,
    invalid_phase: float,
) -> None:
    """A controlled invalid variant retains its field-specific DQ reason."""
    invalid = {**molecule_sample["records"][0], "max_phase": invalid_phase}
    batch = next(molecule_cache.rglob("*.jsonl.zst"))
    payload = zstd.ZstdDecompressor().decompress(batch.read_bytes())
    batch.write_bytes(
        zstd.ZstdCompressor().compress(payload + json.dumps(invalid).encode() + b"\n")
    )
    context = replace(_cached_context(molecule_cache), limit=3)
    await bootstrap_pipeline_runner(context).run()

    silver = await get_silver_records(e2e_data_dir, "chembl_molecule")
    gold = await get_gold_records(e2e_data_dir, "chembl_molecule")
    expected = molecule_sample["expected_phases"]
    assert {row["molecule_id"]: row["max_phase"] for row in silver} == expected
    assert {row["molecule_id"]: row["max_phase"] for row in gold} == expected
    assert len(silver) == len(gold) == 2
    _assert_gold_contract(gold)
    rejected = await _read_delta_records(e2e_data_dir / "output" / "quarantine")
    assert len(rejected) == 1
    assert rejected[0]["error_code"] == "INVALID_DATA"
    assert "max_phase" in json.loads(rejected[0]["error_details"])["message"]
    assert json.loads(rejected[0]["payload"])["max_phase"] == invalid_phase
    reports = list((e2e_data_dir / "run-reports").rglob("pipeline-run-report.json"))
    assert len(reports) == 1
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    silver_stage = next(
        stage for stage in report["funnel"] if stage["stage_id"] == "silver"
    )
    assert silver_stage["unaccounted"] == 0
    assert silver_stage["removals"] == [
        {
            "reason_code": "INVALID_DATA:max_phase",
            "reason_family": "dq",
            "outcome": "quarantined",
            "count": 1,
        }
    ]
