"""Composite evidence remains verifiable when reports move between operating systems."""

import json

import pytest

from bioetl.application.services.run_reports.artifact_digest import (
    canonical_report_sha256,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.interfaces.http._selected_run_artifact_probes import probe_child_artifact
from bioetl.interfaces.http._selected_run_artifact_probes import _artifact_probes
from bioetl.interfaces.http._recent_run_presentation import _evidence_status

pytestmark = pytest.mark.unit


def test_verified_child_keeps_unsupported_replay_distinct_from_error(
    evidence, monkeypatch
):
    from bioetl.application.services.control_plane.manifest.diagnostics.selected_run_replay_readiness import (
        project_selected_run_replay_readiness,
    )
    from bioetl.interfaces.http import _recent_run_presentation as presentation

    root, path, item = evidence
    probes, present = _artifact_probes({"artifacts": [item]}, root)
    readiness = project_selected_run_replay_readiness(
        identity={
            "pipeline_name": "composite_publication",
            "run_id": "parent",
            "status": "success",
        },
        manifest={
            "strict_exact_replay_supported": False,
            "replay_capability": "rebuild_only",
        },
        artifact_probes=probes,
        inventory_present=present,
    )
    assert readiness["verdict"] == "UNSUPPORTED"
    monkeypatch.setattr(
        presentation,
        "load_selected_run_status",
        lambda **kwargs: {
            "evidence_availability": "AVAILABLE",
            "evidence_completeness": "COMPLETE",
            "replay_checks": readiness["checks"],
            "replay_readiness_now": readiness["verdict"],
        },
    )
    displayed = presentation.recent_run_presentation(
        {"pipeline": "composite_publication", "run_id": "parent"},
        root=root,
        manifest_port=None,
    )
    assert displayed["saved_evidence_status"] == "OK"
    assert displayed["replay_readiness_status"] == "N/A"
    path.unlink()
    probes, present = _artifact_probes({"artifacts": [item]}, root)
    blocked = project_selected_run_replay_readiness(
        identity={"status": "success"},
        manifest={"strict_exact_replay_supported": False},
        artifact_probes=probes,
        inventory_present=present,
    )
    assert blocked["verdict"] == "BLOCKED"


@pytest.fixture
def evidence(tmp_path):
    draft = build_pipeline_run_report(
        identity={
            "pipeline_name": "chembl_publication",
            "run_id": "child",
            "manifest_id": "manifest",
            "status": "success",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:01:00+00:00",
        },
        metrics={},
    )
    saved = write_pipeline_run_report(
        draft, root=tmp_path, store=FileRunReportStoreAdapter()
    )
    root = tmp_path / "pipeline/composite_publication/parent"
    root.mkdir(parents=True)
    item = {
        "kind": "composite_child_run_report",
        "pipeline_name": "chembl_publication",
        "run_id": "child",
        "manifest_id": "manifest",
        "ref": "reports/run-reports/pipeline/chembl_publication/child/pipeline-run-report.json",
    }
    return root, saved.json_path, item


@pytest.mark.parametrize(
    "prefix", ["reports/run-reports/", "C:/old/reports/", "/app/reports/"]
)
@pytest.mark.parametrize("separator", ["/", "\\"])
@pytest.mark.parametrize("digest", [False, True])
def test_portable_child_is_verified_without_mutating_saved_evidence(
    evidence, prefix, separator, digest
):
    root, path, item = evidence
    before = path.read_bytes()
    item["ref"] = (
        prefix + "pipeline/chembl_publication/child/pipeline-run-report.json"
    ).replace("/", separator)
    if digest:
        item["sha256"] = canonical_report_sha256(json.loads(before))
    probes, present = _artifact_probes({"artifacts": [item]}, root)
    assert present
    assert probes[0]["result"] == "pass"
    assert probes[0]["reason"] == ("digest_matches" if digest else "snapshot_verified")
    assert (
        _evidence_status(
            {
                "evidence_availability": "AVAILABLE",
                "evidence_completeness": "COMPLETE",
                "replay_checks": probes,
            }
        )
        == "OK"
    )
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "defect,reason",
    [
        ("missing", "artifact_missing"),
        ("traversal", "artifact_path_escape"),
        ("digest", "digest_mismatch"),
        ("identity", "artifact_record_invalid"),
        ("manifest", "artifact_record_invalid"),
        ("snapshot", "artifact_record_invalid"),
        ("revision", "artifact_record_invalid"),
        ("suffix", "artifact_record_invalid"),
    ],
)
def test_child_verification_rejects_incomplete_or_altered_evidence(
    evidence, defect, reason
):
    root, path, item = evidence
    if defect == "missing":
        path.unlink()
    elif defect == "traversal":
        item["ref"] = "../" + item["ref"]
    elif defect == "digest":
        item["sha256"] = "0" * 64
    elif defect == "manifest":
        item["manifest_id"] = "other"
    elif defect == "suffix":
        item["ref"] = item["ref"].replace("/child/", "/other/")
    elif defect == "revision":
        for revision in (path.parent / "status-revisions").glob("*.json"):
            revision.unlink()
    else:
        payload = json.loads(path.read_text())
        if defect == "identity":
            payload["identity"]["run_id"] = "other"
        else:
            payload["identity"]["status"] = "failed"
        path.write_text(json.dumps(payload), encoding="utf-8")
    assert probe_child_artifact(root, item["ref"], item) == ("fail", reason)


def test_unsigned_legacy_child_does_not_pass_by_presence_alone(evidence):
    root, path, item = evidence
    payload = json.loads(path.read_text())
    payload.pop("selected_run_snapshot")
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert probe_child_artifact(root, item["ref"], item) == (
        "unknown",
        "digest_not_recorded",
    )


@pytest.mark.parametrize(
    "invalid", ["../other", "..", "", "a/b", "a\\b", "C:other", None]
)
def test_invalid_child_identity_cannot_choose_a_path(evidence, invalid):
    root, _, item = evidence
    item["run_id"] = invalid
    assert probe_child_artifact(root, item["ref"], item) == (
        "fail",
        "artifact_record_invalid",
    )


def test_child_symlink_cannot_escape_catalog(evidence, tmp_path):
    root, path, item = evidence
    outside = tmp_path / "outside.json"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    try:
        path.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable on this host: {error}")
    assert probe_child_artifact(root, item["ref"], item) == (
        "fail",
        "artifact_path_escape",
    )
