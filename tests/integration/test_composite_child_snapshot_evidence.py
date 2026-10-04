"""Archived child evidence retains strict identity, digest and revision checks."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.run_reports.composite_evidence import (
    snapshot_child_reports,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report
from bioetl.domain.run_reports.selected_status import DOMAINS
from bioetl.infrastructure.control_plane.archive_run_reports import (
    selected_report_sources,
)
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.interfaces.http._selected_run_artifact_probes import _artifact_probes

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "damage,reason",
    [
        (None, "child_evidence_verified"),
        ("digest", "child_digest_mismatch"),
        ("revision", "child_evidence_invalid"),
        ("missing_revision", "child_evidence_invalid"),
        ("identity", "child_evidence_invalid"),
        ("manifest", "child_manifest_mismatch"),
        ("escape", "artifact_path_escape"),
        ("non_green", "child_evidence_not_green"),
    ],
)
def test_captured_child_keeps_strict_assessment_and_archive_revision(
    tmp_path, damage, reason
):
    store = FileRunReportStoreAdapter()
    draft = build_pipeline_run_report(
        identity={
            "pipeline_name": "chembl_activity",
            "run_id": "child",
            "status": "success",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:01:00+00:00",
        },
        metrics={},
    )
    draft = replace(
        draft,
        observations={
            name: {
                "verdict": "WARN"
                if damage == "non_green" and name == "Provider"
                else "OK",
                "reason": "checked",
                "facts": {"count": 0},
            }
            for name in DOMAINS[1:]
        },
    )
    source = write_pipeline_run_report(
        draft, root=tmp_path / "source", store=store
    ).json_path
    child = RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name="chembl_activity",
        run_id="child",
        run_type="incremental",
        run_report_json_path=str(source),
    )
    root = tmp_path / "reports"
    parent = root / "pipeline/composite_activity/parent"
    artifacts = snapshot_child_reports([child], parent, store)
    item = dict(artifacts[0])
    captured = parent / item["ref"]
    revision = next((captured.parent / "status-revisions").glob("*.json"))
    if damage == "digest":
        captured.write_bytes(captured.read_bytes() + b" ")
    elif damage == "revision":
        revision.write_text("{}")
    elif damage == "missing_revision":
        revision.unlink()
    elif damage == "identity":
        item["run_id"] = "foreign"
    elif damage == "manifest":
        item["manifest_id"] = "foreign-manifest"
    elif damage == "escape":
        item["ref"] = "../outside.json"
    probes, present = _artifact_probes({"artifacts": [item]}, parent)
    assert present
    assert probes[0]["reason"] == reason
    assert probes[0]["result"] == ("pass" if damage is None else "fail")
    if damage is None:
        payload = {
            "identity": {"pipeline_name": "composite_activity", "run_id": "parent"},
            "artifacts": [item],
        }
        (parent / "pipeline-run-report.json").write_text(json.dumps(payload))
        manifest = SimpleNamespace(pipeline_name="composite_activity", run_id="parent")
        archived = selected_report_sources(root, manifest)
        assert captured in archived.values()
        assert revision in archived.values()


def test_legacy_external_child_reference_remains_archivable(tmp_path):
    root = tmp_path / "reports"
    parent = root / "pipeline/composite_activity/parent"
    parent.mkdir(parents=True)
    report = parent / "pipeline-run-report.json"
    report.write_text(
        json.dumps(
            {
                "identity": {"pipeline_name": "composite_activity", "run_id": "parent"},
                "artifacts": [
                    {
                        "kind": "composite_child_run_report",
                        "ref": "pipeline/chembl_activity/child/pipeline-run-report.json",
                        "sha256": "old-canonical-digest",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = SimpleNamespace(pipeline_name="composite_activity", run_id="parent")
    assert list(selected_report_sources(root, manifest).values()) == [report]


@pytest.mark.parametrize(
    "raw", ['{"identity": []}', '{"identity": {"run_id": "foreign"}}', "invalid-json"]
)
def test_invalid_child_capture_records_incomplete_without_losing_parent_evidence(
    tmp_path, raw
):
    from bioetl.application.services.run_reports.composite_evidence import (
        capture_child_report_artifacts,
    )
    from bioetl.application.services.run_reports.observations import (
        bind_run_observations,
        reset_run_observations,
        run_observations,
    )

    source = tmp_path / "child.json"
    source.write_text(raw, encoding="utf-8")
    child = RunResult(
        PipelineRunResult.SUCCESS,
        "chembl_activity",
        "child",
        "incremental",
        run_report_json_path=str(source),
    )
    token = bind_run_observations()
    try:
        capture_child_report_artifacts(
            [child], tmp_path / "parent", FileRunReportStoreAdapter()
        )
        evidence = run_observations()["Control Plane"]
        assert evidence["verdict"] == "INCOMPLETE"
        assert evidence["reason"] == "child_report_capture_failed"
    finally:
        reset_run_observations(token)
