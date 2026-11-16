"""Preservation and rejection tests for additive target recovery candidates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import DeltaTable, write_deltalake

from bioetl.infrastructure.storage.target_fk_repair import (
    freeze_target_baseline,
    publish_repair_candidate,
    read_recovered_target_source,
)


def _write(path: Path, records: list[dict], *, partition: bool = False) -> None:
    write_deltalake(
        path,
        pa.Table.from_pylist(records),
        partition_by=["target_type"] if partition else None,
    )


def _row(target_id: str) -> dict:
    return {
        "target_id": target_id,
        "target_type": "SINGLE PROTEIN",
        "entity_id": f"chembl:{target_id}",
        "content_hash": f"frozen-{target_id}",
        "pref_name": f"Original {target_id}",
    }


def make_source(root: Path, ids: list[str], records: list[dict] | None = None) -> Path:
    """Create explicitly synthetic but byte-verified official-response fixtures."""
    root.mkdir(parents=True)
    payloads = {
        "targets": {
            "targets": records or [{"target_chembl_id": x} for x in ids],
            "page_meta": {"total_count": len(ids), "next": None},
        },
        "status": {"chembl_db_version": "ChEMBL_37"},
    }
    receipts = []
    for role, value in payloads.items():
        data = json.dumps(value).encode()
        (root / f"{role}.json").write_bytes(data)
        receipts.append(
            {
                "role": role,
                "url": f"https://www.ebi.ac.uk/chembl/api/data/{role}.json",
                "http_status": 200,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "retrieved_at": "2026-11-16T17:23:02+00:00",
            }
        )
    (root / "acquisition.json").write_text(json.dumps(receipts), encoding="utf-8")
    return root


@pytest.fixture
def repair_case(tmp_path):
    baseline = tmp_path / "baseline"
    _write(baseline / "silver", [_row("CHEMBL1"), _row("CHEMBL2")], partition=True)
    _write(baseline / "gold", [_row("CHEMBL1"), _row("CHEMBL2")])
    _write(baseline / "assay", [{"target_id": "CHEMBL1"}, {"target_id": "CHEMBL3"}])
    frozen = freeze_target_baseline(
        *(baseline / layer for layer in ("silver", "gold", "assay"))
    )
    source = read_recovered_target_source(
        make_source(tmp_path / "source", ["CHEMBL3"]), expected_ids=frozen.missing_ids
    )
    isolated = tmp_path / "isolated"
    for layer in ("silver", "gold"):
        _write(
            isolated / "output" / layer / "chembl/target",
            [_row("CHEMBL3")],
            partition=layer == "silver",
        )
    return frozen, source, isolated


def test_additive_candidate_preserves_every_field_hash_and_unused_target(
    repair_case, tmp_path
):
    baseline, source, isolated = repair_case
    path = publish_repair_candidate(
        baseline,
        isolated_data_root=isolated,
        destination=tmp_path / "candidate",
        source=source,
        execution={"run_id": "synthetic-test"},
    )
    document = json.loads(path.read_bytes())
    assert document["status"] == "validated_candidate"
    assert document["new_source"]["provider_release"] == "ChEMBL_37"
    assert document["baseline"]["gold"]["provider_release"] == "NOT_VERIFIED"
    assert document["baseline"]["silver"]["partition_columns"] == ["target_type"]
    for name in ("silver", "gold", "assay"):
        original = getattr(baseline, name)
        copied = document["frozen_inputs"][name]
        assert copied["files"] == original.files
        assert copied["version"] == original.version
        assert Path(copied["path"]).is_relative_to(path.parent)
    assert document["frozen_inputs"]["new_source"]["row_count"] == 1
    for layer in ("silver", "gold"):
        rows = (
            DeltaTable(path.parent / layer / "chembl/target")
            .to_pyarrow_table()
            .to_pylist()
        )
        assert {x["target_id"] for x in rows} == {"CHEMBL1", "CHEMBL2", "CHEMBL3"}
        assert {x["target_id"]: x for x in rows}["CHEMBL2"] == _row("CHEMBL2")
    baseline.verify_unchanged()


def test_source_byte_mutation_is_rejected(repair_case, tmp_path):
    baseline, source, isolated = repair_case
    path = baseline.silver.path / "_delta_log" / "00000000000000000000.json"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="bytes changed"):
        publish_repair_candidate(
            baseline,
            isolated_data_root=isolated,
            destination=tmp_path / "candidate",
            source=source,
            execution={},
        )
    assert not (tmp_path / "candidate").exists()


def test_gold_filter_loss_blocks_publication(repair_case, tmp_path):
    baseline, source, isolated = repair_case
    target = isolated / "output/gold/chembl/target"
    write_deltalake(target, pa.Table.from_pylist([_row("CHEMBL4")]), mode="overwrite")
    with pytest.raises(ValueError, match="gold output"):
        publish_repair_candidate(
            baseline,
            isolated_data_root=isolated,
            destination=tmp_path / "candidate",
            source=source,
            execution={},
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("http_status", 500),
        ("bytes", 1),
        ("sha256", "0" * 64),
        ("url", "https://example.org/targets"),
    ],
)
def test_acquisition_receipt_is_verified(tmp_path, field, value):
    source = make_source(tmp_path / "source", ["CHEMBL3"])
    path = source / "acquisition.json"
    receipt = json.loads(path.read_bytes())
    receipt[0][field] = value
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError):
        read_recovered_target_source(source, expected_ids={"CHEMBL3"})


def test_source_exact_missing_cohort_is_required(tmp_path):
    source = make_source(tmp_path / "source", ["CHEMBL3"])
    with pytest.raises(ValueError, match="exact missing"):
        read_recovered_target_source(source, expected_ids={"CHEMBL3", "CHEMBL4"})


def test_candidate_overlap_with_baseline_is_rejected(repair_case):
    baseline, source, isolated = repair_case
    with pytest.raises(ValueError, match="overlaps"):
        publish_repair_candidate(
            baseline,
            isolated_data_root=isolated,
            destination=baseline.silver.path / "candidate",
            source=source,
            execution={},
        )


def test_acquisition_changed_after_verification_cannot_receive_completed_manifest(
    repair_case, tmp_path
):
    baseline, source, isolated = repair_case
    receipt = source.directory / "acquisition.json"
    document = json.loads(receipt.read_bytes())
    document[0]["retrieved_at"] = "2026-11-17T00:00:00+00:00"
    receipt.write_text(json.dumps(document), encoding="utf-8")
    destination = tmp_path / "candidate"
    with pytest.raises(ValueError, match="acquisition bytes"):
        publish_repair_candidate(
            baseline,
            isolated_data_root=isolated,
            destination=destination,
            source=source,
            execution={},
        )
    assert not (destination / "manifest.json").exists()
