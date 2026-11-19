# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
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

#13199 (AUD-003/RF-005): Gold Delta + max_phase + identity/hash + SCD2.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from bioetl.domain.exceptions.validation import ValidationError
from bioetl.domain.normalization.profiles.chembl_molecule import (
    normalize_molecule_max_phase,
)
from bioetl.domain.schemas.constants import MAX_PHASE_VALUES

from .conftest import (
    assert_bronze_files_exist,
    assert_gold_table_has_records,
    assert_silver_table_has_records,
    create_test_context,
    get_gold_records,
    get_silver_records,
    managed_e2e_data_dir,
    run_pipeline_or_skip_transient,
)
from tests.helpers.e2e_schema_assertions import assert_records_have_required_fields

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")

_CONTENT_HASH_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_CANONICAL_PHASES = frozenset(MAX_PHASE_VALUES)
# Cassette test_chembl_molecule_full_cycle.yaml carries string phases
# "1.0".."4.0"; approved phase 4 must survive to Silver and Gold.
_APPROVED_PHASE = 4


def _assert_identity_and_hash(records: list[dict], *, entity_label: str) -> None:
    """Assert deterministic identity + hex64 content_hash on every record."""
    assert records, f"No records to check identity/hash for {entity_label}"
    seen_ids: dict[str, str] = {}
    for record in records:
        molecule_id = record.get("molecule_id")
        entity_id = record.get("entity_id")
        content_hash = record.get("content_hash")
        assert isinstance(molecule_id, str) and molecule_id.startswith("CHEMBL"), (
            f"{entity_label}: bad molecule_id={molecule_id!r}"
        )
        assert isinstance(entity_id, str) and entity_id, (
            f"{entity_label}: missing entity_id for {molecule_id}"
        )
        assert isinstance(content_hash, str) and _CONTENT_HASH_HEX64.match(
            content_hash
        ), f"{entity_label}: bad content_hash={content_hash!r} for {molecule_id}"
        # Same business id must map to one stable identity within a layer.
        if molecule_id in seen_ids:
            assert seen_ids[molecule_id] == entity_id, (
                f"{entity_label}: unstable entity_id for {molecule_id}"
            )
        seen_ids[molecule_id] = entity_id


def _assert_canonical_phases(records: list[dict], *, entity_label: str) -> set:
    """Assert every max_phase is a canonical quasi-enum code or None."""
    phases = set()
    for record in records:
        phase = record.get("max_phase")
        assert phase is None or phase in _CANONICAL_PHASES, (
            f"{entity_label}: out-of-universe max_phase={phase!r}"
        )
        # Invalid fractionals (1.5/4.9/5) must never reach Silver/Gold.
        assert phase not in (1.5, 4.9, 5, "1.5", "4.9", "5.0"), (
            f"{entity_label}: invalid fractional max_phase={phase!r} leaked through"
        )
        phases.add(phase)
    return phases


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_molecule_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Molecule pipeline from fetch through Gold.

    Verifies:
    1. Molecule data is fetched and transformed
    2. Silver table contains expected records
    3. Structural data fields are present
    4. Gold table is materialized (sink.gold.mode=scd2) with the same
       eligible molecule ids as Silver (Gold Delta eligible ID/count)
    5. max_phase values are canonical quasi-enum codes in Silver AND Gold
    6. Identity (entity_id) + content_hash (hex64) hold in both layers
    """
    # Arrange
    ctx = create_test_context("chembl_molecule", limit=5)

    # Act
    await run_pipeline_or_skip_transient(ctx)

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "molecule")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = await assert_silver_table_has_records(
        e2e_data_dir, "chembl_molecule", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = await get_silver_records(e2e_data_dir, "chembl_molecule")
    assert_records_have_required_fields(
        records,
        ("molecule_id",),
        entity_label="chembl_molecule.silver",
    )

    # Assert - max_phase canonical codes in Silver (incl. approved 4.0)
    silver_phases = _assert_canonical_phases(records, entity_label="silver")
    assert _APPROVED_PHASE in silver_phases or 4.0 in silver_phases, (
        f"silver must carry approved phase 4 from cassette, got {sorted(silver_phases, key=repr)}"
    )

    # Assert - identity + content_hash in Silver
    _assert_identity_and_hash(records, entity_label="silver")

    # Assert - Gold layer (config sink.gold.mode=scd2)
    gold_count = await assert_gold_table_has_records(
        e2e_data_dir, "chembl_molecule", expected_min=1
    )
    assert gold_count >= 1

    gold_records = await get_gold_records(e2e_data_dir, "chembl_molecule")
    assert_records_have_required_fields(
        gold_records,
        ("molecule_id",),
        entity_label="chembl_molecule.gold",
    )

    # Assert - Gold Delta eligible ID/count: every Gold id must be a Silver id,
    # and first-run SCD2 current rows must match Silver 1:1.
    silver_ids = {r["molecule_id"] for r in records}
    gold_ids = {r["molecule_id"] for r in gold_records}
    assert gold_ids, "Gold must carry at least one eligible molecule id"
    assert gold_ids <= silver_ids, (
        f"Gold ids not eligible from Silver: {sorted(gold_ids - silver_ids)}"
    )
    assert gold_count == silver_count, (
        f"first-run SCD2 Gold current rows ({gold_count}) must equal "
        f"Silver rows ({silver_count})"
    )

    # Assert - max_phase canonical codes in Gold, matching Silver per id.
    gold_phases = _assert_canonical_phases(gold_records, entity_label="gold")
    assert gold_phases <= silver_phases | {None}, (
        f"Gold phases {sorted(gold_phases, key=repr)} exceed Silver phases "
        f"{sorted(silver_phases, key=repr)}"
    )
    silver_phase_by_id = {r["molecule_id"]: r.get("max_phase") for r in records}
    for gold in gold_records:
        assert gold.get("max_phase") == silver_phase_by_id[gold["molecule_id"]], (
            f"Gold max_phase drift for {gold['molecule_id']}: "
            f"{gold.get('max_phase')!r} != {silver_phase_by_id[gold['molecule_id']]!r}"
        )

    # Assert - identity + content_hash in Gold
    _assert_identity_and_hash(gold_records, entity_label="gold")


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_molecule_structural_fields(e2e_data_dir: Path):
    """E2E: Verify structural identity fields for molecules (schema-backed)."""
    ctx = create_test_context("chembl_molecule", limit=5)
    await run_pipeline_or_skip_transient(ctx)
    records = await get_silver_records(e2e_data_dir, "chembl_molecule")
    assert_records_have_required_fields(
        records,
        ("molecule_id",),
        entity_label="chembl_molecule.structural",
    )


@pytest.mark.e2e
@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.asyncio
async def test_chembl_molecule_gold_scd2_idempotent(e2e_data_dir: Path):
    """Replay offline into the same root and a fresh independent root."""
    ctx = create_test_context("chembl_molecule", limit=5)
    await run_pipeline_or_skip_transient(ctx)

    silver_count = await assert_silver_table_has_records(
        e2e_data_dir, "chembl_molecule", expected_min=1
    )
    gold_count = await assert_gold_table_has_records(
        e2e_data_dir, "chembl_molecule", expected_min=1
    )
    silver_rows = await get_silver_records(e2e_data_dir, "chembl_molecule")
    gold_rows = await get_gold_records(e2e_data_dir, "chembl_molecule")

    # One current Gold row per eligible Silver id: no extra versions on build.
    assert sorted(r["molecule_id"] for r in gold_rows) == sorted(
        r["molecule_id"] for r in silver_rows
    )
    assert gold_count == silver_count

    # SCD2 writes must include bookkeeping columns on every current v1 row.
    for row in gold_rows:
        assert {"_is_current", "_version", "_valid_from"} <= row.keys(), (
            f"SCD2 bookkeeping missing for {row.get('molecule_id')}"
        )
        assert row["_is_current"] is True, (
            f"SCD2 row for {row.get('molecule_id')} not current"
        )
        assert row["_version"] == 1, (
            f"SCD2 row for {row.get('molecule_id')} over-versioned on "
            f"fresh build: {row['_version']!r}"
        )
        assert row["_valid_from"], (
            f"SCD2 row for {row.get('molecule_id')} missing _valid_from"
        )

    # The committed entity config must declare the rerun-safe SCD2 contract.
    repo_root = Path(__file__).resolve().parents[2]
    entity_cfg = yaml.safe_load(
        (repo_root / "configs" / "entities" / "chembl" / "molecule.yaml").read_text(
            encoding="utf-8"
        )
    )
    gold_sink = entity_cfg["pipeline"]["sink"]["gold"]
    assert gold_sink["mode"] == "scd2", f"Gold sink mode drift: {gold_sink!r}"
    assert gold_sink["idempotency_contract"] == "scd2", (
        f"Gold idempotency contract drift: {gold_sink!r}"
    )

    # Keep the first Delta table intact: a second real pipeline execution must
    # not append duplicate current rows or increment unchanged versions.
    await run_pipeline_or_skip_transient(
        create_test_context("chembl_molecule", limit=5)
    )
    repeated = await get_gold_records(e2e_data_dir, "chembl_molecule")
    assert len(repeated) == len(gold_rows)
    assert sorted(
        (r["molecule_id"], r["entity_id"], r["content_hash"], r["max_phase"])
        for r in repeated
    ) == sorted(
        (r["molecule_id"], r["entity_id"], r["content_hash"], r["max_phase"])
        for r in gold_rows
    )
    assert all(r["_is_current"] is True and r["_version"] == 1 for r in repeated)

    # A separate storage root changes occurrence metadata, but not identities,
    # normalized phases, or semantic content hashes in either layer.
    fresh_dir = e2e_data_dir.parent / "independent_snapshot"
    with managed_e2e_data_dir(fresh_dir):
        await run_pipeline_or_skip_transient(
            create_test_context("chembl_molecule", limit=5)
        )
        for original, replayed in (
            (silver_rows, await get_silver_records(fresh_dir, "chembl_molecule")),
            (gold_rows, await get_gold_records(fresh_dir, "chembl_molecule")),
        ):
            assert sorted(
                (r["molecule_id"], r["entity_id"], r["content_hash"], r["max_phase"])
                for r in replayed
            ) == sorted(
                (r["molecule_id"], r["entity_id"], r["content_hash"], r["max_phase"])
                for r in original
            )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4.0", 4),
        (4.0, 4),
        ("0.5", 0.5),
        (0.5, 0.5),
        ("-1.0", -1),
        (-1, -1),
        ("0.0", 0),
        (0, 0),
        (None, None),
    ],
)
def test_molecule_max_phase_canonical_codes_preserved(raw, expected) -> None:
    """Local: approved 4.0 and 0.5 (incl. 0.5-numeric) survive normalization.

    No network/VCR: exercises the profile normalizer directly so the
    composite seed 0.5 passthrough has a pinned canonical source.
    """
    assert normalize_molecule_max_phase(raw) == expected
    assert type(normalize_molecule_max_phase(raw)) is type(expected)


@pytest.mark.parametrize("raw", [1.5, 4.9, 5, "1.5", "4.9", "5.0"])
def test_molecule_max_phase_invalid_fractionals_rejected(raw) -> None:
    """Local: invalid fractionals fail with the negative reason code path."""
    try:
        normalize_molecule_max_phase(raw)
    except ValidationError as error:
        assert error.field == "max_phase"
        assert error.reason_code == "INVALID_DATA:max_phase"
    else:  # pragma: no cover - normalizer must reject
        raise AssertionError(f"max_phase={raw!r} was not rejected")


def test_molecule_golden_hash_and_composite_seed_passthrough() -> None:
    """Local: committed fixtures pin hash + composite seed 0.5 passthrough.

    - tests/golden/normalization/chembl/molecule.json pins a hex64
      content_hash for a 0.5-phase record (identity/hash surface).
    - configs/composites/molecule.yaml seed (chembl_molecule) exposes the
      molecule join identity so a 0.5 seed record passes through enrichment.
    """
    repo_root = Path(__file__).resolve().parents[2]
    golden_path = (
        repo_root / "tests" / "golden" / "normalization" / "chembl" / "molecule.json"
    )
    assert golden_path.exists(), f"missing committed golden fixture {golden_path}"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    assert _CONTENT_HASH_HEX64.match(golden["content_hash"]), (
        f"golden content_hash not hex64: {golden['content_hash']!r}"
    )
    # 0.5-numeric canonical code survives to the golden record (not truncated).
    assert golden["normalized"]["max_phase"] == 0.5

    composite_path = repo_root / "configs" / "composites" / "molecule.yaml"
    assert composite_path.exists(), f"missing committed config {composite_path}"
    composite = yaml.safe_load(composite_path.read_text(encoding="utf-8"))
    seed = composite["composite"]["seed"]
    assert seed["pipeline"] == "chembl_molecule"
    assert "molecule_id" in seed["output_keys"], (
        f"seed must carry molecule join identity, got {seed['output_keys']}"
    )
