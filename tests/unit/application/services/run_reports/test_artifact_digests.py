"""Canonical run-report artifact digests (#11796)."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from bioetl.application.services.run_reports.artifact_digest import (
    canonical_report_sha256,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.run_reports.pipeline_assembly import build_pipeline_run_report
from bioetl.domain.run_reports.selected_status import verify_snapshot
from bioetl.interfaces.http._selected_run_artifact_probes import _artifact_probes
from tests.helpers.run_report_store import MemoryReportStore

pytestmark = pytest.mark.unit


def test_late_observation_rebinds_self_digest_and_preserves_old_revision(
    tmp_path: Path,
) -> None:
    from bioetl.application.services.run_reports.snapshots import publish_snapshot

    store = MemoryReportStore()
    report = build_pipeline_run_report(
        identity={
            "pipeline_name": "chembl_activity",
            "run_id": "late",
            "status": "success",
        },
        metrics={},
    )
    written = write_pipeline_run_report(report, root=tmp_path, store=store)
    original = json.loads(store.read_text(str(written.json_path)))
    previous = original["selected_run_snapshot"]
    previous_path = (
        written.json_path.parent / "status-revisions" / f"{previous['revision']}.json"
    )
    retained = store.read_text(previous_path.as_posix())
    candidate = {k: v for k, v in original.items() if k != "selected_run_snapshot"}
    candidate["observations"] = {
        "Workflow": {"verdict": "OK", "reason": "workflow_success"}
    }
    published = publish_snapshot(candidate, written.json_path, store=store)
    own = next(
        a for a in published["artifacts"] if a["kind"] == "pipeline_run_report_json"
    )
    assert own["sha256"] == canonical_report_sha256(published)
    assert published["selected_run_snapshot"]["revision"] != previous["revision"]
    assert verify_snapshot(published["selected_run_snapshot"])
    assert store.read_text(previous_path.as_posix()) == retained


def test_writer_hashes_selected_store_even_when_local_path_exists(
    tmp_path: Path,
) -> None:
    from bioetl.application.services.run_reports.writer import _stored_sha256

    path = tmp_path / "report.md"
    path.write_bytes(b"unrelated local file")
    store = MemoryReportStore()
    store.write_text(str(path), "selected backend\r\n")
    assert (
        _stored_sha256(path, store)
        == hashlib.sha256(b"selected backend\r\n").hexdigest()
    )


def test_file_store_digest_preserves_newline_bytes(tmp_path: Path) -> None:
    from bioetl.infrastructure.storage.run_report_store_adapter import (
        FileRunReportStoreAdapter,
    )

    path = tmp_path / "report.md"
    raw = b"first\r\nsecond\r\n"
    path.write_bytes(raw)
    assert (
        FileRunReportStoreAdapter().sha256(str(path)) == hashlib.sha256(raw).hexdigest()
    )


def test_writer_records_canonical_json_and_markdown_digests(tmp_path: Path) -> None:
    store = MemoryReportStore()
    report = build_pipeline_run_report(
        identity={
            "pipeline_name": "chembl_publication_term",
            "run_id": "run-digest-1",
            "status": "success",
        },
        metrics={},
    )
    written = write_pipeline_run_report(report, root=tmp_path, store=store)
    payload = json.loads(store.read_text(str(written.json_path)))
    artifacts = {item["kind"]: item for item in payload["artifacts"]}
    json_sha = artifacts["pipeline_run_report_json"]["sha256"]
    md_sha = artifacts["pipeline_run_report_md"]["sha256"]
    assert json_sha == canonical_report_sha256(payload)
    assert md_sha
    assert verify_snapshot(payload["selected_run_snapshot"])
    latest = json.loads(store.read_text(str(written.latest_path)))
    assert latest["json_sha256"] == json_sha
    assert latest["markdown_sha256"] == md_sha


def test_artifact_probes_digest_matches_for_new_self_reports(tmp_path: Path) -> None:
    from bioetl.infrastructure.storage.run_report_store_adapter import (
        FileRunReportStoreAdapter,
    )

    store = FileRunReportStoreAdapter()
    report = build_pipeline_run_report(
        identity={
            "pipeline_name": "chembl_publication_term",
            "run_id": "run-digest-2",
            "status": "success",
        },
        metrics={},
    )
    written = write_pipeline_run_report(report, root=tmp_path, store=store)
    payload = json.loads(Path(written.json_path).read_text(encoding="utf-8"))
    probes, present = _artifact_probes(payload, written.json_path.parent)
    assert present is True
    reasons = {probe["reason"] for probe in probes}
    assert "digest_matches" in reasons
    assert "digest_mismatch" not in reasons


def test_artifact_probes_keep_object_available_without_digest(tmp_path: Path) -> None:
    report_dir = tmp_path / "pipeline" / "chembl_activity" / "legacy"
    report_dir.mkdir(parents=True)
    json_path = report_dir / "pipeline-run-report.json"
    md_path = report_dir / "pipeline-run-report.md"
    json_path.write_text("{}", encoding="utf-8")
    md_path.write_text("legacy", encoding="utf-8")
    payload = {
        "artifacts": [
            {"kind": "pipeline_run_report_json", "ref": str(json_path.as_posix())},
            {"kind": "pipeline_run_report_md", "ref": str(md_path.as_posix())},
        ]
    }
    probes, present = _artifact_probes(payload, report_dir)
    assert present is True
    assert {probe["reason"] for probe in probes} == {"object_available"}
