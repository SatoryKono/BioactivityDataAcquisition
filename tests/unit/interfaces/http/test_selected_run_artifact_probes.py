"""Persisted artifact evidence respects run scope and digest availability."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from bioetl.interfaces.http import _selected_run_bronze_binding as bronze_binding
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


@pytest.mark.parametrize(
    ("source_root", "digest_matches", "expected"),
    [
        ("attempt", True, "digest_matches"),
        ("attempt", False, "digest_mismatch"),
        ("ATTEMPT", True, "digest_matches"),
        ("foreign", True, None),
        ("foreign/../attempt", True, "artifact_path_escape"),
    ],
)
def test_windows_bronze_reference_uses_the_bound_data_root(
    tmp_path, source_root, digest_matches, expected
):
    alias = tmp_path / "data"
    data_root = alias / "attempt"
    suffix = "chembl/target/2026-11-25/batch.jsonl.zst"
    artifact = data_root / "output/bronze" / suffix
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"saved-bronze")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    report = {
        "artifacts": [
            {
                "kind": "bronze_batch",
                "ref": f"D:/repo/data/{source_root}/output/bronze/{suffix}",
                "sha256": digest if digest_matches else "0" * 64,
            }
        ]
    }
    context = SimpleNamespace(data_root=data_root, trusted_alias_base=alias)
    probes, present = _artifact_probes(report, tmp_path, context=context)
    assert present
    if expected is None:
        assert probes[0]["result"] == "fail"
    else:
        assert probes[0]["reason"] == expected


def test_rejected_windows_bronze_reference_fails_closed_despite_matching_digest(
    tmp_path,
):
    """An absolute Windows bronze_batch link outside the bound root must fail.

    The recorded SHA-256 of an existing foreign file must not rescue the
    probe: rejected references never reach the generic absolute-path resolver.
    """
    alias = tmp_path / "data"
    data_root = alias / "attempt"
    foreign = tmp_path / "foreign" / "output" / "bronze"
    foreign.mkdir(parents=True)
    payload = b"foreign-bronze"
    outsider = foreign / "batch.jsonl.zst"
    outsider.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    report = {
        "artifacts": [
            {
                "kind": "bronze_batch",
                "ref": "D:/foreign/data/unbound/output/bronze/batch.jsonl.zst",
                "sha256": digest,
            }
        ]
    }
    context = SimpleNamespace(data_root=data_root, trusted_alias_base=alias)
    probes, present = _artifact_probes(report, tmp_path, context=context)
    assert present
    assert probes[0]["result"] == "fail"
    assert probes[0]["reason"] == "artifact_path_escape"


@pytest.mark.parametrize(
    ("mode", "digest_payload", "expected"),
    [
        ("native", b"recorded", "digest_matches"),
        ("native_mismatch", b"bound", "digest_mismatch"),
        ("stat_denied", b"bound", "digest_matches"),
        ("open_denied", b"bound", "digest_matches"),
        ("bound_mismatch", b"recorded", "digest_mismatch"),
        ("both_unreadable", b"bound", "artifact_unreadable"),
        ("traversal", b"recorded", "artifact_path_escape"),
    ],
)
def test_windows_bronze_reference_native_priority_and_fallback(
    tmp_path, monkeypatch, mode, digest_payload, expected
):
    alias = tmp_path / "data"
    root = alias / "attempt"
    suffix = Path("chembl/target/2026-11-25/batch.jsonl.zst")
    native_root = tmp_path / "original" / alias.name
    recorded = native_root / root.name / "output/bronze" / suffix
    bound = root / "output/bronze" / suffix
    recorded.parent.mkdir(parents=True)
    recorded.write_bytes(b"recorded")
    bound.parent.mkdir(parents=True)
    bound.write_bytes(b"bound")

    prefix = native_root.as_posix()
    if sys.platform != "win32":
        prefix = "D:/original/data"
        monkeypatch.setattr(
            bronze_binding, "_native_absolute_artifact", lambda _: recorded
        )
    (native_root / "foreign").mkdir()
    relative_root = "foreign/../attempt" if mode == "traversal" else root.name
    report = {
        "artifacts": [
            {
                "kind": "bronze_batch",
                "ref": f"{prefix}/{relative_root}/output/bronze/{suffix.as_posix()}",
                "sha256": hashlib.sha256(digest_payload).hexdigest(),
            }
        ]
    }
    context = SimpleNamespace(data_root=root, trusted_alias_base=alias)
    real_is_file, real_open = Path.is_file, Path.open

    def check_file(path):
        if path == recorded and mode == "stat_denied":
            raise PermissionError("stat denied")
        return real_is_file(path)

    def open_file(path, *args, **kwargs):
        if path == recorded and mode in {
            "open_denied",
            "bound_mismatch",
            "both_unreadable",
        }:
            raise PermissionError("recorded open denied")
        if path == bound and mode == "both_unreadable":
            raise PermissionError("bound copy open denied")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "is_file", check_file)
    monkeypatch.setattr(Path, "open", open_file)
    probes, present = _artifact_probes(report, tmp_path, context=context)
    assert present
    assert probes[0]["reason"] == expected


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
