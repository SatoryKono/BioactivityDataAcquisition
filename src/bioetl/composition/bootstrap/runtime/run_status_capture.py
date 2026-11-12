"""Bind persisted control-plane status capture independently of archive execution."""

from __future__ import annotations

from pathlib import Path
from dataclasses import replace

from bioetl.domain.ports import MetricsPort, RawRunManifestInspectionPort
from bioetl.application.services.run_reports.paths import resolve_report_root
from bioetl.infrastructure.control_plane.file_evidence_read_context import (
    FileEvidenceReadContext,
    _SelectedRootLedgerPort,
)

from bioetl.application.observability.control_plane_archive import (
    resolve_control_plane_archive_root,
)
from bioetl.application.observability import control_plane_evidence
from bioetl.application.services.run_reports import control_plane_snapshot
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
import bioetl.infrastructure.control_plane.file_run_manifest_store as manifest_store


def create_run_status_capture(
    data_root: str | Path,
    *,
    archive_root: Path | None = None,
    report_root: Path | None = None,
) -> control_plane_snapshot.CaptureControlPlaneSnapshot:
    """Bind historical capture to the same local control-plane root as execution."""
    root = Path(data_root) / "output" / "control"
    manifests = manifest_store.FileRunManifestStore(base_path=root / "run_manifest")
    resolved_archive = resolve_control_plane_archive_root(archive_root)
    return control_plane_snapshot.CaptureControlPlaneSnapshot(
        manifests=manifests,
        evidence=control_plane_evidence.ControlPlaneEvidenceService(
            ledger_port=FileRunLedgerStore(base_path=root / "run_ledger"),
            lineage_store=FileLineageStore(base_path=root / "lineage"),
            manifest_inspector=manifests,
            lifecycle_planner=FileControlPlaneArtifactLifecycleStore(base_path=root),
            archive_verifier=FileArchiveStore(
                Path(data_root), resolved_archive, report_root
            ),
        ),
    )


def bind_selected_evidence_validation(
    context: FileEvidenceReadContext,
    *,
    archive_root: Path | None,
    report_root: Path | None,
    metrics: MetricsPort | None,
) -> FileEvidenceReadContext:
    """Compose validation ports on the same selected root as persisted status capture."""
    output_root = context.data_root / "output" / "control"
    if archive_root is not None:
        report_root = resolve_report_root(root=report_root)
        archive_verifier: FileArchiveStore | None = FileArchiveStore(
            context.data_root, archive_root, report_root
        )
    else:
        archive_verifier = None
    if isinstance(context.manifest_port, RawRunManifestInspectionPort):
        manifest_inspector: RawRunManifestInspectionPort | None = context.manifest_port
    else:
        manifest_inspector = None
    validation_service = control_plane_evidence.ControlPlaneEvidenceService(
        ledger_port=_SelectedRootLedgerPort(context),
        lineage_store=context.lineage_port,
        manifest_inspector=manifest_inspector,
        lifecycle_planner=FileControlPlaneArtifactLifecycleStore(
            base_path=output_root, metrics=metrics
        ),
        archive_verifier=archive_verifier,
    )
    return replace(context, validation_service=validation_service)
