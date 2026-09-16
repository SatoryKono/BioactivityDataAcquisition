"""Finalize child workflow evidence as an explicit late revision, preserving history."""

from __future__ import annotations

import json
import re
from pathlib import Path

from bioetl.application.services.run_reports.snapshots import publish_snapshot
from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.run_reports.models import WorkflowExecutionRow, WorkflowRunReport
from bioetl.domain.run_reports.selected_status import verify_snapshot


def _child_path(root: Path, row: WorkflowExecutionRow) -> Path:
    """Reject invalid persisted identity before resolving the report path."""
    parts = (str(row.pipeline_name), str(row.pipeline_run_id))
    if any(
        part in {".", ".."} or re.fullmatch(r"[\w.-]+", part) is None for part in parts
    ):
        raise ValueError("workflow_child_identity_invalid")
    return root / "pipeline" / parts[0] / parts[1] / "pipeline-run-report.json"


def _verified_child(
    path: Path,
    row: WorkflowExecutionRow,
    workflow_id: object,
    store: RunReportStorePort,
) -> dict[str, object] | None:
    """Load a snapshot bound to this exact child and workflow, skipping legacy data."""
    if not store.is_file(str(path)):
        return None
    child = json.loads(store.read_text(str(path)))
    if not isinstance(child, dict):
        raise ValueError("workflow_child_report_corrupt")
    snapshot = child.get("selected_run_snapshot")
    if snapshot is None:
        return None
    evidence = {
        key: value for key, value in child.items() if key != "selected_run_snapshot"
    }
    if (
        not isinstance(snapshot, dict)
        or not verify_snapshot(snapshot)
        or snapshot.get("evidence") != evidence
    ):
        raise ValueError("workflow_child_snapshot_corrupt")
    _validate_child_identity(child, row, workflow_id)
    return child


def _validate_child_identity(
    child: dict[str, object], row: WorkflowExecutionRow, workflow_id: object
) -> None:
    """Require exact workflow ownership independently of snapshot integrity."""
    identity = child.get("identity", {})
    expected = {
        "run_id": row.pipeline_run_id,
        "pipeline_name": row.pipeline_name,
        "workflow_run_id": workflow_id,
    }
    if row.pipeline_manifest_id is not None:
        expected["manifest_id"] = row.pipeline_manifest_id
    if not isinstance(identity, dict) or any(
        identity.get(key) != value for key, value in expected.items()
    ):
        raise ValueError("workflow_child_identity_mismatch")


def finalize_workflow_children(
    report: WorkflowRunReport, *, root: Path, store: RunReportStorePort
) -> None:
    """Publish late workflow observations only for verified, explicitly bound children."""
    identity = report.identity
    status = str(identity.get("status", "unknown"))
    verdict = {
        "success": "OK",
        "failed": "ERROR",
        "partial": "WARN",
        "cancelled": "WARN",
        "shutdown": "WARN",
    }.get(status, "UNKNOWN")
    for row in report.execution:
        if not row.pipeline_name or not row.pipeline_run_id:
            continue
        path = _child_path(root, row)
        child = _verified_child(path, row, identity.get("workflow_run_id"), store)
        if child is None:
            continue
        observations = child.setdefault("observations", {})
        if not isinstance(observations, dict):
            raise ValueError("workflow_child_observations_corrupt")
        observations["Workflow"] = {
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
