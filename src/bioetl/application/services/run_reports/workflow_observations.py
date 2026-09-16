"""Finalize child workflow evidence as an explicit late revision, preserving history."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.application.services.run_reports.snapshots import publish_snapshot
from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.run_reports.models import WorkflowRunReport
from bioetl.domain.run_reports.selected_status import verify_snapshot


def finalize_workflow_children(
    report: WorkflowRunReport, *, root: Path, store: RunReportStorePort
) -> None:
    """Update only verified child reports explicitly bound to this workflow run."""
    identity = report.identity
    for row in report.execution:
        if not row.pipeline_name or not row.pipeline_run_id:
            continue
        parts = (row.pipeline_name, row.pipeline_run_id)
        if any(
            not part
            or part in {".", ".."}
            or any(not (c.isalnum() or c in "._-") for c in part)
            for part in parts
        ):
            raise ValueError("workflow_child_identity_invalid")
        path = (
            root
            / "pipeline"
            / row.pipeline_name
            / row.pipeline_run_id
            / "pipeline-run-report.json"
        )
        if not store.is_file(str(path)):
            continue
        child = json.loads(store.read_text(str(path)))
        if not isinstance(child, dict):
            raise ValueError("workflow_child_report_corrupt")
        snapshot = child.get("selected_run_snapshot")
        if snapshot is None:
            continue  # No retrospective invention of evidence for legacy runs.
        evidence = {
            key: value for key, value in child.items() if key != "selected_run_snapshot"
        }
        if (
            not isinstance(snapshot, dict)
            or not verify_snapshot(snapshot)
            or snapshot.get("evidence") != evidence
        ):
            raise ValueError("workflow_child_snapshot_corrupt")
        child_identity = child.get("identity", {})
        if (
            child_identity.get("run_id") != row.pipeline_run_id
            or child_identity.get("pipeline_name") != row.pipeline_name
            or child_identity.get("workflow_run_id") != identity.get("workflow_run_id")
        ):
            raise ValueError("workflow_child_identity_mismatch")
        status = str(identity.get("status", "unknown"))
        verdict = {
            "success": "OK",
            "failed": "ERROR",
            "partial": "WARN",
            "cancelled": "WARN",
            "shutdown": "WARN",
        }.get(status, "UNKNOWN")
        child.setdefault("observations", {})["Workflow"] = {
            "verdict": verdict,
            "reason": f"workflow_{status}",
            "facts": {
                "identity": dict(identity),
                "step_id": row.step_id,
                "step_status": row.status,
            },
        }
        child.pop("selected_run_snapshot", None)
        payload = publish_snapshot(child, path, store=store)
        store.write_text(
            str(path),
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        )
