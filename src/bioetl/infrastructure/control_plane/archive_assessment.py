"""Archive assessment staging and verification (#11250)."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from bioetl.infrastructure.control_plane.archive_run_reports import (
    selected_report_sources,
)
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)

if TYPE_CHECKING:
    from bioetl.domain.control_plane import (
        ControlPlaneArtifactLifecyclePlan,
        RunManifest,
    )


def refresh_archived_assessment(
    *,
    data_root: Path,
    archive_root: Path,
    report_root: Path,
    manifest: RunManifest,
    plan: ControlPlaneArtifactLifecyclePlan,
    observed_at: datetime,
    capture_factory: Callable[[], Callable[[str, str, datetime], None]],
    bind_observations: Callable[[], object],
    reset_observations: Callable[[object], None],
    control_plane_observation: Callable[[], object],
    publish_snapshot: Callable[..., object],
    write_json: Callable[..., None],
) -> tuple[bool | None, str]:
    """Stage, verify, and publish an archived run assessment."""
    archive = FileArchiveStore(data_root, archive_root, report_root)
    verified, reason = archive.verify(manifest=manifest, plan=plan)
    if verified is not True:
        return verified, reason
    sources = selected_report_sources(report_root, manifest)
    report_paths = [p for p in sources.values() if p.name == "pipeline-run-report.json"]
    if not report_paths:
        return verified, reason
    report_path = report_paths[0]
    original = report_path.read_bytes()
    report = json.loads(original)
    if not isinstance(report.get("selected_run_snapshot"), dict):
        return None, "archive_assessment_requires_snapshot"
    token = bind_observations()
    try:
        capture_factory()(manifest.pipeline_name, str(manifest.run_id), observed_at)
        observation = control_plane_observation()
    finally:
        reset_observations(token)
    report.pop("selected_run_snapshot")
    report.setdefault("observations", {})["Control Plane"] = observation
    report["assessment_at"] = observed_at.isoformat()
    store = FileRunReportStoreAdapter()
    with TemporaryDirectory(prefix="bioetl-archive-assessment-") as temporary:
        staged_root = Path(temporary)
        relative = report_path.relative_to(report_root.resolve())
        staged_path = staged_root / relative
        for source in sources.values():
            target = staged_root / source.relative_to(report_root.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        candidate = publish_snapshot(report, staged_path, store=store)
        write_json(staged_path, candidate, store=store)
        staged_archive = FileArchiveStore(data_root, archive_root, staged_root)
        valid, why = staged_archive.verify(manifest=manifest, plan=plan)
        if why == "archive_evidence_not_recorded":
            staged_archive.create(manifest=manifest, plan=plan)
            valid, why = staged_archive.verify(manifest=manifest, plan=plan)
        if valid is not True:
            return valid, why
        if report_path.read_bytes() != original:
            return False, "archive_report_changed_during_assessment"
        unchanged, why = archive.verify(manifest=manifest, plan=plan)
        if unchanged is not True:
            return unchanged, why
        committed = publish_snapshot(report, report_path, store=store)
        if committed != candidate:
            raise ValueError("archive_assessment_candidate_mismatch")
        write_json(report_path, committed, store=store)
    return archive.verify(manifest=manifest, plan=plan)
