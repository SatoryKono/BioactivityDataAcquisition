"""Include selected-run reports and revisions in the existing local archive pack."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.run_reports.selected_status import verify_snapshot


def _load_report(path: Path, manifest: RunManifest) -> dict[str, object]:
    """Read a JSON report only when its identity matches the archive manifest."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("archive_report_corrupt")
    identity = payload.get("identity", {})
    if (
        not isinstance(identity, dict)
        or identity.get("run_id") != str(manifest.run_id)
        or identity.get("pipeline_name") != manifest.pipeline_name
    ):
        raise ValueError("archive_report_identity_mismatch")
    return payload


def _revision_sources(payload: dict[str, object], revisions: Path) -> list[Path]:
    """Require a valid committed revision before including its history."""
    snapshot = payload.get("selected_run_snapshot")
    if snapshot is None:
        return []
    if not isinstance(snapshot, dict) or not verify_snapshot(snapshot):
        raise ValueError("archive_report_snapshot_corrupt")
    evidence = {
        key: value for key, value in payload.items() if key != "selected_run_snapshot"
    }
    if snapshot.get("evidence") != evidence:
        raise ValueError("archive_report_evidence_mismatch")
    committed = revisions / f"{snapshot['revision']}.json"
    if not committed.is_file():
        raise ValueError("archive_report_revision_missing")
    if json.loads(committed.read_text(encoding="utf-8")) != snapshot:
        raise ValueError("archive_report_revision_mismatch")
    return sorted(revisions.glob("*.json"))


def _validate_source(item: Path, base: Path, revisions: Path) -> None:
    """Reject escaped paths and corrupt historical revisions before archiving."""
    if (
        item.is_symlink()
        or item.parent.is_symlink()
        or not item.resolve().is_relative_to(base)
    ):
        raise ValueError("archive_report_symlink_rejected")
    if item.parent == revisions:
        revision = json.loads(item.read_text(encoding="utf-8"))
        if (
            not isinstance(revision, dict)
            or not verify_snapshot(revision)
            or item.stem != revision.get("revision")
        ):
            raise ValueError("archive_report_revision_corrupt")


def selected_report_sources(
    root: Path | None, manifest: RunManifest
) -> dict[str, Path]:
    """Enumerate only an exact, identity-checked report and its immutable revisions."""
    if root is None:
        return {}
    base = root.resolve()
    folder = base / "pipeline" / manifest.pipeline_name / str(manifest.run_id)
    if not folder.resolve().is_relative_to(base):
        raise ValueError("archive_report_outside_root")
    path = folder / "pipeline-run-report.json"
    if not path.is_file():
        return {}
    payload = _load_report(path, manifest)
    revisions = folder / "status-revisions"
    files = [path, *_revision_sources(payload, revisions)]
    result = {}
    for item in files:
        _validate_source(item, base, revisions)
        result[f"run-reports/{item.relative_to(base).as_posix()}"] = item
    return result
