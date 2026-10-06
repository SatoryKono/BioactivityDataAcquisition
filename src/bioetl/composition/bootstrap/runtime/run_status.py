"""Composition of persisted run-status capture using existing local stores."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.observability.control_plane_archive import (
    resolve_control_plane_archive_root,
)
from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
)
from bioetl.application.services.run_reports.control_plane_snapshot import (
    CaptureControlPlaneSnapshot,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)


def create_run_status_capture(
    data_root: str | Path,
    *,
    archive_root: Path | None = None,
    report_root: Path | None = None,
) -> CaptureControlPlaneSnapshot:
    """Bind historical capture to the same local control-plane root as execution."""
    root = Path(data_root) / "output" / "control"
    manifests = FileRunManifestStore(base_path=root / "run_manifest")
    resolved_archive = resolve_control_plane_archive_root(archive_root)
    return CaptureControlPlaneSnapshot(
        manifests=manifests,
        evidence=ControlPlaneEvidenceService(
            ledger_port=FileRunLedgerStore(base_path=root / "run_ledger"),
            lineage_store=FileLineageStore(base_path=root / "lineage"),
            manifest_inspector=manifests,
            lifecycle_planner=FileControlPlaneArtifactLifecycleStore(base_path=root),
            archive_verifier=FileArchiveStore(
                Path(data_root), resolved_archive, report_root
            ),
        ),
    )
