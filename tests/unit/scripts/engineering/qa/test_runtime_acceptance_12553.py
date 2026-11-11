"""Evidence integrity checks, independent of product lifecycle acceptance."""

from __future__ import annotations

import json
import hashlib
import io
import re
import tomllib
import sys
import xml.etree.ElementTree as ET

import pytest

from scripts.engineering.qa import runtime_acceptance_12553 as capture
from scripts.engineering.qa import runtime_acceptance_12553_coverage as coverage
from tests.helpers import runtime_acceptance_12553 as observer

pytestmark = pytest.mark.unit


def test_nonzero_command_preserves_both_raw_streams_and_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(capture, "BUNDLE", tmp_path)
    code = capture.capture(
        "nonzero",
        [
            sys.executable,
            "-c",
            "import sys;sys.stdout.buffer.write(b'out\\r\\n');sys.stderr.buffer.write(b'err\\n');sys.exit(7)",
        ],
    )
    assert code == 7
    assert (tmp_path / "nonzero-stdout.txt").read_bytes() == b"out\r\n"
    assert (tmp_path / "nonzero-stderr.txt").read_bytes() == b"err\n"
    receipt = json.loads((tmp_path / "nonzero-command.json").read_text())
    assert receipt["exit_code"] == 7
    assert len(receipt["head_sha"]) == len(receipt["tree_sha"]) == 40
    with pytest.raises(FileExistsError):
        capture.capture("nonzero", [sys.executable, "-c", "pass"])


def test_register_accounts_for_every_identity_without_changing_inventory():
    catalog = coverage.ROOT / "configs/quality/external_resource_inventory.json"
    before = catalog.read_bytes()
    result = coverage.build()
    rows = result["resources"]
    assert len(rows) == len({r["identity"] for r in rows}) == 207
    assert sum(result["families"].values()) == 207
    assert not result["full_runtime_acceptance"]
    for row in rows:
        assert row["reason"]
        assert row["trace_refs"] or row["status"] == "NOT_VERIFIABLE"
        assert all(
            capture.evidence_exists(ref, coverage.BUNDLE) for ref in row["trace_refs"]
        )
        assert set(row["scenarios"]) == {
            "normal",
            "error",
            "cancellation",
            "timeout",
            "retry",
        }
        assert all(
            s["runtime_result"] == "NOT_RUN_12553" for s in row["scenarios"].values()
        )
    assert catalog.read_bytes() == before


def test_unknown_trace_identity_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(coverage, "BUNDLE", tmp_path)
    for run in coverage.RUNS:
        (tmp_path / f"{run}-events.json").write_text(
            json.dumps({"events": [{"identities": ["invented-resource"]}]})
        )
    with pytest.raises(ValueError, match="unknown observed resource"):
        coverage.build()


def _write_control(root, prefix="qualified-review-controls", **changes):
    receipt = {
        "exit_code": changes.get("exit_code", 0),
        "timed_out": changes.get("timed_out", False),
    }
    (root / f"{prefix}-command.json").write_text(json.dumps(receipt))
    (root / f"{prefix}-exit-code.txt").write_text(str(changes.get("exit_code", 0)))
    (root / f"{prefix}-stdout.txt").write_text("real pytest output")
    suite = ET.Element("testsuite", tests="5", failures="0", errors="0", skipped="0")
    for name in sorted(coverage.LOCK_TESTS):
        ET.SubElement(suite, "testcase", name=name)
    ET.ElementTree(suite).write(root / f"{prefix}-junit.xml")


@pytest.mark.parametrize(
    "failure",
    [
        "exit",
        "timeout",
        "skip",
        "failure",
        "error",
        "empty",
        "missing-receipt",
        "missing-exit",
        "missing-stdout",
        "malformed",
    ],
)
def test_lock_boundary_fails_closed(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(coverage, "BUNDLE", tmp_path)
    _write_control(tmp_path)
    prefix = tmp_path / "qualified-review-controls"
    if failure in {"exit", "timeout"}:
        _write_control(
            tmp_path,
            exit_code=7 if failure == "exit" else 0,
            timed_out=failure == "timeout",
        )
    elif failure.startswith("missing-"):
        suffix = {
            "missing-receipt": "command.json",
            "missing-exit": "exit-code.txt",
            "missing-stdout": "stdout.txt",
        }[failure]
        (tmp_path / f"qualified-review-controls-{suffix}").unlink()
    elif failure == "malformed":
        prefix.with_name(prefix.name + "-junit.xml").write_text("<broken")
    else:
        path = prefix.with_name(prefix.name + "-junit.xml")
        tree = ET.parse(path)
        suite = tree.getroot()
        if failure == "empty":
            suite.clear()
        else:
            tag = {"skip": "skipped", "failure": "failure", "error": "error"}[failure]
            ET.SubElement(suite[0], tag)
        tree.write(path)
    assert coverage.lock_control()[0] is False


def test_missing_lock_evidence_never_asserts_a_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(coverage, "BUNDLE", tmp_path)
    control = coverage.lock_control()
    resource = {
        "identity": "diagnostics.metric_inventory.reentrant-lock",
        "type": "reentrant-lock",
        "creation_sites": [],
        "creator": [],
        "owner": "collector",
        "closer": "release",
        "shutdown_contract": "release lock",
        "scenarios": {
            name: {"observation": "required barrier"}
            for name in ("normal", "error", "cancellation", "timeout", "retry")
        },
    }
    row = coverage._resource_row(resource, [], control)
    assert row["status"] == "NOT_VERIFIABLE"
    assert all(
        s["register_result"] == "NOT_VERIFIABLE" for s in row["scenarios"].values()
    )


def test_failed_qualified_control_cannot_fall_back_to_older_success(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(coverage, "BUNDLE", tmp_path)
    _write_control(tmp_path, prefix="review-controls")
    _write_control(tmp_path, exit_code=1)
    assert coverage.lock_control()[0] is False


def test_complete_lock_control_can_assert_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(coverage, "BUNDLE", tmp_path)
    _write_control(tmp_path)
    assert coverage.lock_control()[0] is True


def test_observer_provenance_requires_matching_executed_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(coverage, "BUNDLE", tmp_path)
    trace = tmp_path / "qualified-files-config-final-events.json.gz"
    trace.write_bytes(b"trace")
    (tmp_path / "qualified-files-config-final-command.json").write_text(
        json.dumps(
            {"input_sha256": {"tests/helpers/runtime_acceptance_12553.py": "0" * 64}}
        )
    )
    with pytest.raises(ValueError, match="unqualified observer version"):
        coverage._observer_provenance(trace)


def test_archive_preserves_raw_bytes_and_reads_without_extraction(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(capture, "BUNDLE", tmp_path)
    (tmp_path / "README.md").write_bytes(b"baseline document\r\n")
    stream = b"raw stdout\r\n"
    (tmp_path / "run-stdout.txt").write_bytes(stream)
    (tmp_path / "run-stderr.txt").write_bytes(b"")
    capture.pack(baseline_names={"README.md"})
    assert (tmp_path / "README.md").is_file()
    assert not (tmp_path / "run-stdout.txt").exists()
    assert capture.read_evidence("run-stdout.txt", tmp_path) == stream
    assert capture.read_evidence("run-stderr.txt", tmp_path) == b""
    manifest = json.loads(capture.read_evidence("artifact-sha256.json", tmp_path))
    for name, digest in manifest.items():
        assert (
            hashlib.sha256(capture.read_evidence(name, tmp_path)).hexdigest() == digest
        )
    (tmp_path / "run-stdout.txt").write_bytes(b"later run\n")
    capture.pack(baseline_names={"README.md"})
    assert capture.read_evidence("run-stdout.txt", tmp_path) == b"later run\n"


def test_published_bundle_integrity_accepts():
    capture.verify(capture.BUNDLE)


def test_observer_retains_the_real_handle_for_closure_inspection(tmp_path, monkeypatch):
    monkeypatch.setattr(observer, "ACTIVE", "probe")
    monkeypatch.setattr(observer, "EVENTS", [])
    monkeypatch.setattr(observer, "HANDLES", [])
    monkeypatch.setattr(
        observer, "_identities", lambda kinds: (["probe.file"], ["probe.py:1"])
    )
    wrapped_open = observer._observe_open(io.open)
    with wrapped_open(tmp_path / "fixture.txt", "w") as handle:
        assert not handle.closed
        assert observer.HANDLES[0][1] is handle
    assert observer.HANDLES[0][1].closed
    assert observer.EVENTS[0]["event"] == "opened"


def test_observer_records_allocation_failure_without_inventing_handle(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(observer, "ACTIVE", "probe")
    monkeypatch.setattr(observer, "EVENTS", [])
    monkeypatch.setattr(observer, "HANDLES", [])
    monkeypatch.setattr(
        observer, "_identities", lambda kinds: (["probe.file"], ["probe.py:1"])
    )
    with pytest.raises(FileNotFoundError):
        observer._observe_open(io.open)(tmp_path / "missing.txt")
    assert not observer.HANDLES
    assert observer.EVENTS[0]["event"] == "allocation-error"


def _runtime_metadata_exception():
    config = tomllib.loads(
        (capture.ROOT / ".gitleaks.toml").read_text(encoding="utf-8")
    )
    generic = next(rule for rule in config["rules"] if rule["id"] == "generic-api-key")
    entry = next(
        a
        for a in generic["allowlists"]
        if a["description"].startswith("Reviewed #12553")
    )
    assert config["extend"]["useDefault"] is True
    assert entry["condition"] == "AND"
    assert entry["regexTarget"] == "line"
    assert not entry.get("commits")
    assert not entry.get("stopwords")
    assert len(entry["paths"]) == 26
    assert len(entry["regexes"]) == 34
    return entry


def _runtime_metadata_allowed(path, line):
    entry = _runtime_metadata_exception()
    return any(re.search(pattern, path) for pattern in entry["paths"]) and any(
        re.search(pattern, line) for pattern in entry["regexes"]
    )


def test_reviewed_source_digest_is_allowed_only_in_its_receipt():
    receipt = json.loads(
        capture.read_evidence("evidence-contracts-command.json", capture.BUNDLE)
    )
    source = "src/bioetl/application/composite/dependency_key_resolvers.py"
    value = receipt["input_sha256"][source]
    line = json.dumps(source) + ": " + json.dumps(value) + ","
    path = "reports/audit-runs/12553-runtime-acceptance/evidence-contracts-command.json"
    assert _runtime_metadata_allowed(path, line)
    assert _runtime_metadata_allowed(path, "\n    " + line + "\r\n")
    assert not _runtime_metadata_allowed(
        "reports/audit-runs/unrelated/evidence-contracts-command.json", line
    )
    assert not _runtime_metadata_allowed(
        path.replace("evidence-contracts", "unreviewed"), line
    )


def test_unreviewed_credentials_are_not_hidden_by_digest_exception():
    receipt = json.loads(
        capture.read_evidence("evidence-contracts-command.json", capture.BUNDLE)
    )
    source = "src/bioetl/application/composite/dependency_key_resolvers.py"
    known_digest = receipt["input_sha256"][source]
    path = "reports/audit-runs/12553-runtime-acceptance/evidence-contracts-command.json"
    unknown_value = hashlib.sha256(b"controlled-unreviewed-value").hexdigest()
    assert not _runtime_metadata_allowed(
        path, json.dumps(source) + ": " + json.dumps(unknown_value)
    )
    assert not _runtime_metadata_allowed(path, '"api_key": ' + json.dumps(known_digest))
    assert not _runtime_metadata_allowed(
        path,
        json.dumps("src/bioetl/unreviewed_api.py") + ": " + json.dumps(known_digest),
    )
