"""Create or verify a local control-plane archive after a successful pipeline run."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.domain.control_plane import ControlPlaneArtifactLifecyclePolicy, RunManifest
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)

DEFAULT_CONTROL_PLANE_ARCHIVE_ROOT = Path("reports/local/gf14-archive/verified")
_ARCHIVE_FAILURES = (OSError, RuntimeError, TypeError, ValueError, FileExistsError)


def resolve_control_plane_archive_root(archive_root: Path | None) -> Path:
    """Use an explicit root when set; otherwise the reports-local default."""
    if archive_root is not None:
        return Path(archive_root)
    return DEFAULT_CONTROL_PLANE_ARCHIVE_ROOT


def should_archive_control_plane(result: RunResult, options: RunOptions | None) -> bool:
    """Archive only successful, non-dry-run pipeline completions with a manifest."""
    if options is not None and (options.no_control_plane_archive or options.dry_run):
        return False
    return (
        result.status is PipelineRunResult.SUCCESS
        and bool(result.manifest_id)
        and bool(result.run_id)
    )


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
    return _create_or_verify_pack(
        manifest=manifest,
        data_root=resolved_root,
        archive_root=resolve_control_plane_archive_root(archive_root),
        report_root=report_root,
        control_root=control_root,
    )


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
        ControlPlaneArtifactLifecyclePolicy(retention_days=90, now=datetime.now(UTC)),
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
