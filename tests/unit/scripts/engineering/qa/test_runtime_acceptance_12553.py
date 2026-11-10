"""Evidence integrity checks, independent of product lifecycle acceptance."""

from __future__ import annotations

import json
import sys

import pytest

from scripts.engineering.qa import runtime_acceptance_12553 as capture
from scripts.engineering.qa import runtime_acceptance_12553_coverage as coverage

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
        assert all((coverage.BUNDLE / ref).is_file() for ref in row["trace_refs"])
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
