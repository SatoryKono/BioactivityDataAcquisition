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
