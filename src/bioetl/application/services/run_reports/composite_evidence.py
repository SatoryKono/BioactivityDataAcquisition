"""Retain child report evidence inside the parent report's artifact boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.application.services.run_reports.artifact_digest import (
    canonical_report_sha256,
)
from bioetl.domain.ports import RunReportStorePort


def snapshot_child_reports(
    children: list[RunResult], run_root: Path, store: RunReportStorePort
) -> tuple[dict[str, object], ...]:
    """Copy identity-checked child reports to content-addressed local artifacts."""
    artifacts: list[dict[str, object]] = []
    for child in children:
        if not child.run_report_json_path:
            continue
        raw = store.read_text(child.run_report_json_path)
        payload = json.loads(raw)
        identity = payload.get("identity", {}) if isinstance(payload, dict) else {}
        if (
            identity.get("run_id") != child.run_id
            or identity.get("pipeline_name") != child.pipeline_name
        ):
            raise ValueError("Composite child report identity mismatch")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        relative = Path("child-reports") / f"{digest}.json"
        destination = run_root / relative
        store.mkdir(str(destination.parent))
        if not store.is_file(str(destination)):
            store.write_text(str(destination), raw)
        if store.read_text(str(destination)) != raw:
            raise ValueError(
                "Composite child report snapshot differs from captured content"
            )
        _snapshot_child_revision(
            payload, Path(child.run_report_json_path), destination, store
        )
        artifacts.append(
            {
                "kind": "composite_child_run_report",
                "ref": relative.as_posix(),
                "sha256": store.sha256(str(destination)),
                "canonical_sha256": canonical_report_sha256(payload),
                "run_id": child.run_id,
                "pipeline_name": child.pipeline_name,
                "manifest_id": child.manifest_id,
            }
        )
    return tuple(artifacts)


def _snapshot_child_revision(
    payload: dict[str, object],
    source_report: Path,
    destination: Path,
    store: RunReportStorePort,
) -> None:
    """Preserve the verified frozen revision beside a captured child report."""
    snapshot = payload.get("selected_run_snapshot")
    if isinstance(snapshot, dict):
        from bioetl.domain.run_reports.selected_status import verify_snapshot

        if not verify_snapshot(snapshot):
            raise ValueError("Composite child snapshot is corrupt")
        revision = str(snapshot["revision"]) + ".json"
        source_revision = source_report.parent / "status-revisions" / revision
        if store.is_file(str(source_revision)):
            revision_raw = store.read_text(str(source_revision))
            if json.loads(revision_raw) != snapshot:
                raise ValueError("Composite child revision differs from snapshot")
            saved_revision = destination.parent / "status-revisions" / revision
            store.mkdir(str(saved_revision.parent))
            if store.is_file(str(saved_revision)):
                if store.read_text(str(saved_revision)) != revision_raw:
                    raise ValueError("Captured child revision differs from source")
            else:
                store.write_text(str(saved_revision), revision_raw)
