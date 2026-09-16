"""Atomic selected-run report publication with retained content-addressed revisions."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.run_reports.selected_status import build_snapshot


def publish_snapshot(
    report: dict[str, object], path: Path, *, store: RunReportStorePort
) -> dict[str, object]:
    """Publish immutable inputs first; the report itself is the atomic commit record.

    A crash before report publication leaves the previous committed revision intact.
    Concurrent publications can select either complete revision, never a mixed one.
    Identical finalization is a no-op; late evidence creates a different revision.
    """
    report = {**report, "schema_version": "pipeline_run_report_v2"}
    snapshot = build_snapshot(report)
    revision_path = path.parent / "status-revisions" / f"{snapshot['revision']}.json"
    content = (
        json.dumps(
            snapshot, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
        )
        + "\n"
    )
    if store.is_file(str(revision_path)):
        if store.read_text(str(revision_path)) != content:
            raise ValueError("selected-run revision conflict or corruption")
    else:
        store.mkdir(str(revision_path.parent))
        store.write_text(str(revision_path), content)
    return {**report, "selected_run_snapshot": snapshot}
