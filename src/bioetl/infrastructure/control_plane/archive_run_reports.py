"""Include selected-run reports and revisions in the existing local archive pack."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.run_reports.selected_status import verify_snapshot


def selected_report_sources(
    root: Path | None, manifest: RunManifest
) -> dict[str, Path]:
    """Enumerate only an exact, identity-checked report and its immutable revisions."""
    if root is None:
        return {}
    base = root.resolve()
    relative = Path("pipeline") / manifest.pipeline_name / str(manifest.run_id)
    folder = base / relative
    if not folder.resolve().is_relative_to(base):
        raise ValueError("archive_report_outside_root")
    path = folder / "pipeline-run-report.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("archive_report_corrupt")
    identity = payload.get("identity", {})
    if (
        identity.get("run_id") != str(manifest.run_id)
        or identity.get("pipeline_name") != manifest.pipeline_name
    ):
        raise ValueError("archive_report_identity_mismatch")
    files = [path]
    revisions = folder / "status-revisions"
    snapshot = payload.get("selected_run_snapshot")
    if snapshot is not None:
        if not isinstance(snapshot, dict) or not verify_snapshot(snapshot):
            raise ValueError("archive_report_snapshot_corrupt")
        evidence = {
            key: value
            for key, value in payload.items()
            if key != "selected_run_snapshot"
        }
        if snapshot.get("evidence") != evidence:
            raise ValueError("archive_report_evidence_mismatch")
        committed = revisions / f"{snapshot['revision']}.json"
        if not committed.is_file():
            raise ValueError("archive_report_revision_missing")
        if json.loads(committed.read_text(encoding="utf-8")) != snapshot:
            raise ValueError("archive_report_revision_mismatch")
        files.extend(sorted(revisions.glob("*.json")))
    result = {}
    for item in files:
        if (
            item.is_symlink()
            or item.parent.is_symlink()
            or not item.resolve().is_relative_to(base)
        ):
            raise ValueError("archive_report_symlink_rejected")
        if item.parent == revisions:
            revision = json.loads(item.read_text(encoding="utf-8"))
            if not verify_snapshot(revision) or item.stem != revision.get("revision"):
                raise ValueError("archive_report_revision_corrupt")
        result[f"run-reports/{item.relative_to(base).as_posix()}"] = item
    return result
