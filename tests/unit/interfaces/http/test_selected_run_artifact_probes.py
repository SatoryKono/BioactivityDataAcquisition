"""Persisted artifact evidence respects run scope and digest availability."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from bioetl.interfaces.http._selected_run_artifact_probes import _artifact_probes

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("inventory", [None, {}, []])
def test_absent_artifact_inventory_remains_unknown(tmp_path, inventory):
    assert _artifact_probes({"artifacts": inventory}, tmp_path) == ([], False)


@pytest.mark.parametrize(
    ("record", "reason"),
    [
        (None, "artifact_record_invalid"),
        ({"sha256": "a" * 64}, "hash_without_object"),
        ({"path": "  "}, "artifact_path_missing"),
        ({"path": "absent.bin"}, "artifact_missing"),
        ({"path": "../outside.bin"}, "artifact_path_escape"),
        (
            {"path": "reports/nested.json", "kind": "pipeline_run_report_json"},
            "artifact_missing",
        ),
    ],
)
def test_unverifiable_artifact_cannot_pass(tmp_path, record, reason):
    probes, present = _artifact_probes({"artifacts": [record]}, tmp_path)
    assert present is True
    assert probes[0]["result"] == "fail"
    assert probes[0]["reason"] == reason
    assert probes[0]["evidence_ref"] == "#/artifacts/0"


def test_absolute_layer_reference_and_unhashed_object_have_distinct_verdicts(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    layer = tmp_path / "silver.parquet"
    layer.write_bytes(b"persisted-silver")
    digest = hashlib.sha256(layer.read_bytes()).hexdigest()
    probes, _ = _artifact_probes(
        {
            "artifacts": [
                {"kind": "silver", "path": str(layer), "sha256": digest},
                {"kind": "sidecar", "path": str(layer), "sha256": digest},
            ]
        },
        run,
    )
    assert probes[0]["reason"] == "digest_matches"
    assert probes[1]["reason"] == "artifact_path_escape"
    inside = run / "sidecar.bin"
    inside.write_bytes(b"available")
    probes, _ = _artifact_probes({"artifacts": [{"path": str(inside)}]}, run)
    assert probes[0]["result"] == "unknown"
    assert probes[0]["reason"] == "digest_not_recorded"


def test_existing_self_report_needs_no_impossible_self_hash(tmp_path):
    (tmp_path / "pipeline-run-report.md").write_text("report", encoding="utf-8")
    probes, _ = _artifact_probes(
        {
            "artifacts": [
                {"kind": "pipeline_run_report_md", "path": "old/run/report.md"}
            ]
        },
        tmp_path,
    )
    assert probes[0]["result"] == "pass"
    assert probes[0]["reason"] == "object_available"


@pytest.mark.parametrize("digest", ["a" * 64, "actual"])
def test_json_non_mapping_is_hashed_as_bytes(tmp_path, digest):
    report = tmp_path / "pipeline-run-report.json"
    report.write_text("[]", encoding="utf-8")
    if digest == "actual":
        digest = hashlib.sha256(report.read_bytes()).hexdigest()
        expected = "digest_matches"
    else:
        expected = "digest_mismatch"
    probes, _ = _artifact_probes(
        {
            "artifacts": [
                {
                    "kind": "pipeline_run_report_json",
                    "path": report.name,
                    "digest": digest,
                }
            ]
        },
        tmp_path,
    )
    assert probes[0]["reason"] == expected


def test_single_filename_symlink_cannot_escape_selected_run(tmp_path, monkeypatch):
    run = tmp_path / "run"
    run.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"foreign-run-evidence")
    real_resolve = Path.resolve

    def resolve(path, *args, **kwargs):
        if path == run / "linked.bin":
            return outside
        return real_resolve(path, *args, **kwargs)

    # Model filesystem canonicalization portably, including Windows without
    # symlink privileges, while using real files for the evidence objects.
    monkeypatch.setattr(Path, "resolve", resolve)
    probes, _ = _artifact_probes(
        {
            "artifacts": [
                {
                    "path": "linked.bin",
                    "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
                }
            ]
        },
        run,
    )
    assert probes[0]["result"] == "fail"
    assert probes[0]["reason"] == "artifact_path_escape"
