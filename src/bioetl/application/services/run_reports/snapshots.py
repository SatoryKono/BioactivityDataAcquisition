"""Atomic selected-run report publication with retained content-addressed revisions."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.application.services.run_reports.artifact_digest import (
    canonical_report_sha256,
)
from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.run_reports.selected_status import build_snapshot

_PIPELINE_REPORT_SCHEMAS = {"pipeline_run_report_v1", "pipeline_run_report_v2"}


def publish_snapshot(
    report: dict[str, object], path: Path, *, store: RunReportStorePort
) -> dict[str, object]:
    """Publish immutable inputs first; the report itself is the atomic commit record.

    A crash before report publication leaves the previous committed revision intact.
    Concurrent publications can select either complete revision, never a mixed one.
    Identical finalization is a no-op; late evidence creates a different revision.
    """
    if report.get("schema_version") not in _PIPELINE_REPORT_SCHEMAS:
        raise ValueError("pipeline_snapshot_schema_required")
    report = {**report, "schema_version": "pipeline_run_report_v2"}
    # Late archive/workflow observations change the report's canonical content.
    # Bind its self digest to this revision before signing the snapshot.
    artifacts = report.get("artifacts")
    if isinstance(artifacts, list):
        digest = canonical_report_sha256(report)
        report["artifacts"] = [
            {**item, "sha256": digest}
            if isinstance(item, dict) and item.get("kind") == "pipeline_run_report_json"
            else item
            for item in artifacts
        ]
    snapshot = build_snapshot(report)
    revision_path = path.parent / "status-revisions" / f"{snapshot['revision']}.json"
    content = (
        json.dumps(
            snapshot, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
        )
        + "\n"
    )
    revision_key = revision_path.as_posix()
    if store.is_file(revision_key):
        if store.read_text(revision_key) != content:
            raise ValueError("selected-run revision conflict or corruption")
    else:
        store.mkdir(revision_path.parent.as_posix())
        store.write_text(revision_key, content)
    return {**report, "selected_run_snapshot": snapshot}
