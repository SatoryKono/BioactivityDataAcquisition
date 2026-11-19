"""Cached-Bronze Molecule E2E for exact Gold eligibility, phases and SCD2 replay."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml
import zstandard

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.composition.bootstrap import bootstrap_pipeline_runner
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.contracts.gold import ChEMBLMoleculeGoldSchema

from .conftest import (
    create_test_context,
    get_gold_records,
    get_silver_records,
    managed_e2e_data_dir,
)

pytestmark = pytest.mark.usefixtures("strict_dq_env")

_SCD_COLUMNS = {"_is_current", "_valid_from", "_valid_to", "_version"}
_EXPECTED_PHASES = {
    "CHEMBL900001": 4,
    "CHEMBL900002": 0.5,
    "CHEMBL900003": 0.5,
    "CHEMBL900004": None,
}


@pytest.fixture
def molecule_bronze(tmp_path: Path) -> Path:
    """Build synthetic phase/filter cases from a committed provider response."""
    cassette_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures/vcr/chembl/test_chembl_molecule_full_cycle.yaml"
    )
    cassette = yaml.safe_load(cassette_path.read_text(encoding="utf-8"))
    response = json.loads(cassette["interactions"][0]["response"]["body"]["string"])
    template = response["molecules"][0]
    records = []
    for index, phase in enumerate(("4.0", "0.5", 0.5, None, "4.0", "4.0", "4.0"), 1):
        record = deepcopy(template)
        record["molecule_chembl_id"] = f"CHEMBL{900000 + index}"
        record["max_phase"] = phase
        record.pop("potential_duplicate", None)
        records.append(record)
    records[4]["molecule_type"] = "Protein"
    records[5]["structure_type"] = "NONE"
    records[6]["inorganic_flag"] = 1
    bronze = tmp_path / "cached-bronze"
    dated = bronze / "2026-11-18"
    dated.mkdir(parents=True)
    payload = "".join(json.dumps(record) + "\n" for record in records).encode("utf-8")
    (
        dated / "batch_2026-11-18_00000000-0000-0000-0000-000000000001.jsonl.zst"
    ).write_bytes(zstandard.ZstdCompressor().compress(payload))
    return bronze


async def _run_cached_molecules(
    bronze: Path, destination: Path
) -> tuple[list[dict], list[dict]]:
    """Run the normal bootstrap and read physical Delta tables without skip recovery."""
    context = replace(
        create_test_context("chembl_molecule", limit=7),
        cached_bronze=CachedBronzeContext.from_options(
            path=str(bronze), date="2026-11-18"
        ),
    )
    with pytest.MonkeyPatch.context() as paths:
        paths.setenv("BIOETL_REPORT_ROOT", str(destination / "reports"))
        paths.setenv("BIOETL_ARCHIVE_ROOT", str(destination / "archive"))
        with managed_e2e_data_dir(destination):
            runner = bootstrap_pipeline_runner(context)
            await runner.run()
            metrics = runner.execution_metrics
            assert metrics["records_fetched"] == 7
            assert metrics["records_silver"] == 7
            assert metrics["records_gold"] == len(_EXPECTED_PHASES)
            assert metrics["records_quarantined"] == 0
            silver = await get_silver_records(destination, "chembl_molecule")
            gold = await get_gold_records(destination, "chembl_molecule")
    return silver, gold


def _assert_molecule_outputs(silver: list[dict], gold: list[dict]) -> None:
    """Check exact eligibility, normalized hashes and strict persisted Gold schema."""
    assert len(silver) == 7
    assert {row["molecule_id"] for row in silver} == {
        f"CHEMBL{900000 + index}" for index in range(1, 8)
    }
    assert len(gold) == len(_EXPECTED_PHASES)
    assert {row["molecule_id"]: row["max_phase"] for row in gold} == _EXPECTED_PHASES
    silver_by_id = {row["molecule_id"]: row for row in silver}
    normalizer = RecordNormalizationProcessor(provider="chembl", entity_type="molecule")
    for row in silver:
        assert row["content_hash"] == normalizer.compute_content_hash(
            normalizer.normalize_business_data(row)
        )
    for row in gold:
        original = silver_by_id[row["molecule_id"]]
        assert row["max_phase"] == original["max_phase"]
        assert row["entity_id"] == original["entity_id"]
        assert row["content_hash"] == original["content_hash"]
        assert _SCD_COLUMNS <= row.keys()
        assert row["_is_current"] is True
        assert row["_version"] == 1
        assert row["_valid_from"]
        assert row["_valid_to"] is None
    # schema.gold.exclude_fields declares these technical omissions in molecule.yaml.
    schema = ChEMBLMoleculeGoldSchema.to_schema().remove_columns(
        ["_dq_warn", "_dq_error", "_index"]
    )
    assert schema.strict is True
    assert set(gold[0]) == set(schema.columns) | _SCD_COLUMNS

    schema.validate(
        pd.DataFrame(
            [
                {name: value for name, value in row.items() if name not in _SCD_COLUMNS}
                for row in gold
            ]
        ),
        lazy=True,
    )


@pytest.mark.e2e
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_chembl_molecule_cached_phase_and_gold_filters(
    tmp_path: Path,
    molecule_bronze: Path,
) -> None:
    """Decimal provider codes survive the full pipeline and business rejects stay Silver."""
    silver, gold = await _run_cached_molecules(molecule_bronze, tmp_path / "output")
    _assert_molecule_outputs(silver, gold)


@pytest.mark.e2e
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_chembl_molecule_cached_scd2_idempotent(
    tmp_path: Path,
    molecule_bronze: Path,
) -> None:
    """An identical incremental write preserves all physical SCD2 rows and versions."""
    destination = tmp_path / "output"
    first_silver, first_gold = await _run_cached_molecules(molecule_bronze, destination)
    second_silver, second_gold = await _run_cached_molecules(
        molecule_bronze, destination
    )
    _assert_molecule_outputs(first_silver, first_gold)
    _assert_molecule_outputs(second_silver, second_gold)
    assert sorted(first_gold, key=lambda row: row["molecule_id"]) == sorted(
        second_gold, key=lambda row: row["molecule_id"]
    )
    assert {row["molecule_id"]: row["content_hash"] for row in first_silver} == {
        row["molecule_id"]: row["content_hash"] for row in second_silver
    }


@pytest.mark.e2e
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_chembl_molecule_cached_outputs_are_deterministic(
    tmp_path: Path,
    molecule_bronze: Path,
) -> None:
    """Independent processing roots produce identical business records and hashes."""
    first_silver, first_gold = await _run_cached_molecules(
        molecule_bronze, tmp_path / "first"
    )
    second_silver, second_gold = await _run_cached_molecules(
        molecule_bronze, tmp_path / "second"
    )
    _assert_molecule_outputs(first_silver, first_gold)
    _assert_molecule_outputs(second_silver, second_gold)
    assert sorted(first_silver, key=lambda row: row["molecule_id"]) == sorted(
        second_silver, key=lambda row: row["molecule_id"]
    )
    for first, second in zip(
        sorted(first_gold, key=lambda row: row["molecule_id"]),
        sorted(second_gold, key=lambda row: row["molecule_id"]),
        strict=True,
    ):
        assert {
            name: value for name, value in first.items() if name not in _SCD_COLUMNS
        } == {name: value for name, value in second.items() if name not in _SCD_COLUMNS}
