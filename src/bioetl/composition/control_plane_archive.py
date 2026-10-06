"""Compose local control-plane archive I/O after a successful pipeline run."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from bioetl.application.observability.control_plane_archive import (
    resolve_control_plane_archive_root,
    should_archive_control_plane,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    RunOptions,
    RunResult,
)
from bioetl.application.services.run_reports.paths import resolve_report_root
from bioetl.domain.control_plane import ControlPlaneArtifactLifecyclePolicy, RunManifest
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.time import SystemClock

from datetime import datetime
from typing import TYPE_CHECKING
from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    reset_run_observations,
    run_observations,
)
from bioetl.application.services.run_reports.snapshots import publish_snapshot
from bioetl.application.services.run_reports.writer import write_json
from bioetl.composition.bootstrap.runtime.run_status_capture import (
    create_run_status_capture,
)
from bioetl.infrastructure.control_plane.archive_assessment import (
    refresh_archived_assessment as refresh_archived_assessment_impl,
)

if TYPE_CHECKING:
    from bioetl.domain.control_plane import (
        ControlPlaneArtifactLifecyclePlan,
        RunManifest,
    )

_ARCHIVE_FAILURES = (OSError, RuntimeError, TypeError, ValueError, FileExistsError)


def archive_successful_run(
    *,
    result: RunResult,
    options: RunOptions | None,
    data_root: Path,
    archive_root: Path | None,
    report_root: Path | None,
) -> tuple[bool | None, str]:
    """Write a pack when missing, otherwise re-verify. Never overwrite sources."""
    if not should_archive_control_plane(result, options):
        return None, "archive_skipped"
    try:
        run_id = RunID(UUID(str(result.run_id)))
    except ValueError:
        return None, "archive_skipped"
    resolved_root = Path(data_root).resolve()
    control_root = resolved_root / "output" / "control"
    manifests = FileRunManifestStore(base_path=control_root / "run_manifest")
    manifest = manifests.get_by_run_id(run_id)
    if manifest is None or manifest.pipeline_name != result.pipeline_name:
        return None, "archive_manifest_missing"
    report_root = resolve_report_root(root=report_root).resolve()
    outcome = _create_or_verify_pack(
        manifest=manifest,
        data_root=resolved_root,
        archive_root=resolve_control_plane_archive_root(archive_root),
        report_root=report_root,
        control_root=control_root,
    )
    if outcome[0] is not True:
        return outcome
    now = SystemClock().now()
    plan = FileControlPlaneArtifactLifecycleStore(
        base_path=control_root
    ).plan_for_manifest(
        ControlPlaneArtifactLifecyclePolicy(retention_days=90, now=now),
        manifest=manifest,
    )
    try:
        return refresh_archived_assessment(
            data_root=resolved_root,
            archive_root=resolve_control_plane_archive_root(archive_root),
            report_root=report_root.resolve(),
            manifest=manifest,
            plan=plan,
            observed_at=now,
        )
    except _ARCHIVE_FAILURES:
        return False, "archive_assessment_failed"


def _create_or_verify_pack(
    *,
    manifest: RunManifest,
    data_root: Path,
    archive_root: Path,
    report_root: Path | None,
    control_root: Path,
) -> tuple[bool | None, str]:
    archive_root.mkdir(parents=True, exist_ok=True)
    planner = FileControlPlaneArtifactLifecycleStore(base_path=control_root)
    plan = planner.plan_for_manifest(
        ControlPlaneArtifactLifecyclePolicy(retention_days=90, now=SystemClock().now()),
        manifest=manifest,
    )
    if plan.resolution_issues or not plan.artifacts:
        return None, "archive_source_evidence_incomplete"
    store = FileArchiveStore(data_root, archive_root, report_root)
    verified, reason = store.verify(manifest=manifest, plan=plan)
    if reason != "archive_evidence_not_recorded":
        return verified, reason
    try:
        store.create(manifest=manifest, plan=plan)
    except _ARCHIVE_FAILURES:
        return False, "archive_create_failed"
    return store.verify(manifest=manifest, plan=plan)


def refresh_archived_assessment(
    *,
    data_root: Path,
    archive_root: Path,
    report_root: Path,
    manifest: RunManifest,
    plan: ControlPlaneArtifactLifecyclePlan,
    observed_at: datetime,
) -> tuple[bool | None, str]:
    """Wire report-status capture and publish an archived assessment."""
    return refresh_archived_assessment_impl(
        data_root=data_root,
        archive_root=archive_root,
        report_root=report_root,
        manifest=manifest,
        plan=plan,
        observed_at=observed_at,
        capture_factory=lambda: create_run_status_capture(
            data_root,
            archive_root=archive_root,
            report_root=report_root,
        ),
        bind_observations=bind_run_observations,
        reset_observations=reset_run_observations,
        control_plane_observation=lambda: run_observations()["Control Plane"],
        publish_snapshot=publish_snapshot,
        write_json=write_json,
    )
