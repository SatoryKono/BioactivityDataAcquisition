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


@pytest.mark.parametrize("accessible", [True, False])
def test_windows_native_binding_and_inaccessible_fallback(
    tmp_path, monkeypatch, accessible
):
    alias = tmp_path / "data"
    root = alias / "attempt"
    suffix = "chembl/target/2026-11-25/batch.jsonl.zst"
    bound = root / "output/bronze" / suffix
    bound.parent.mkdir(parents=True)
    bound.write_bytes(b"bound")
    native = tmp_path / "native"
    native.write_bytes(b"recorded")
    monkeypatch.setattr(bronze_binding, "_native_absolute_artifact", lambda _: native)
    is_file = Path.is_file

    def check_file(path):
        if path == native and not accessible:
            raise PermissionError("denied")
        return is_file(path)

    monkeypatch.setattr(Path, "is_file", check_file)
    item = {
        "kind": "bronze_batch",
        "ref": f"D:/repo/DATA/attempt/output/bronze/{suffix}",
        "sha256": hashlib.sha256(b"bound").hexdigest(),
    }
    context = SimpleNamespace(data_root=root, trusted_alias_base=alias)
    if accessible:
        assert bronze_binding._bound_bronze_reference(item, context) is item
    else:
        probes, _ = _artifact_probes({"artifacts": [item]}, tmp_path, context=context)
        assert probes[0]["reason"] == "digest_matches"


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


def _probe_recorded_bronze_over_bound_copy(tmp_path):
    """A natively reachable recorded Bronze file is verified in place.

    When the originating host replays its own report, the recorded absolute
    path wins over the bound copy, even if the bound copy holds stale bytes.
    """
    alias = tmp_path / "data"
    data_root = alias / "attempt"
    suffix = "chembl/target/2026-11-25/batch.jsonl.zst"
    recorded = tmp_path / "other" / "data" / "attempt" / "output" / "bronze" / suffix
    recorded.parent.mkdir(parents=True)
    recorded.write_bytes(b"recorded-bronze")
    digest = hashlib.sha256(recorded.read_bytes()).hexdigest()
    stale = data_root / "output" / "bronze" / suffix
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale-bound-copy")
    report = {
        "artifacts": [{"kind": "bronze_batch", "ref": str(recorded), "sha256": digest}]
    }
    context = SimpleNamespace(data_root=data_root, trusted_alias_base=alias)
    return _artifact_probes(report, tmp_path, context=context)


def test_windows_bronze_reference_prefers_recorded_file_over_bound_copy(tmp_path):
    probes, present = _probe_recorded_bronze_over_bound_copy(tmp_path)
    assert present
    assert probes[0]["reason"] == "digest_matches"


@pytest.mark.skipif(
    sys.platform != "win32", reason="native Windows drive-letter binding"
)
def test_windows_bronze_reference_uses_native_branch(tmp_path):
    """On Windows the recorded file must win before any binding rewrite.

    The POSIX run of the sibling test never reaches the native branch:
    ``PureWindowsPath`` treats ``tmp_path`` as relative. Without native
    priority this scenario binds to the stale copy and reports
    ``digest_mismatch`` instead.
    """
    probes, present = _probe_recorded_bronze_over_bound_copy(tmp_path)
    assert present
    assert probes[0]["reason"] == "digest_matches"


@pytest.mark.skipif(
    sys.platform != "win32", reason="native Windows drive-letter binding"
)
def test_windows_bronze_reference_falls_back_when_recorded_unreadable(
    tmp_path, monkeypatch
):
    """An unreadable recorded file must fall back to the bound copy.

    A ``PermissionError`` from the native readability check is an
    unavailability signal, not a probe failure: binding still verifies the
    attested copy by digest.
    """
    alias = tmp_path / "data"
    data_root = alias / "attempt"
    suffix = "chembl/target/2026-11-25/batch.jsonl.zst"
    recorded = tmp_path / "other" / "data" / "attempt" / "output" / "bronze" / suffix
    recorded.parent.mkdir(parents=True)
    recorded.write_bytes(b"recorded-bronze")
    bound = data_root / "output" / "bronze" / suffix
    bound.parent.mkdir(parents=True)
    bound.write_bytes(b"recorded-bronze")
    digest = hashlib.sha256(bound.read_bytes()).hexdigest()
    real_is_file = Path.is_file

    def raising_is_file(self):
        if self == recorded:
            raise PermissionError("denied")
        return real_is_file(self)

    monkeypatch.setattr(Path, "is_file", raising_is_file)
    report = {
        "artifacts": [{"kind": "bronze_batch", "ref": str(recorded), "sha256": digest}]
    }
    context = SimpleNamespace(data_root=data_root, trusted_alias_base=alias)
    probes, present = _artifact_probes(report, tmp_path, context=context)
    assert present
    assert probes[0]["reason"] == "digest_matches"


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
