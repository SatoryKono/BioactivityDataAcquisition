"""Composition of persisted run-status capture using existing local stores."""

from __future__ import annotations

from pathlib import Path
from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.application.services.run_reports.composite import CompositeRunReportService
from bioetl.composition.control_plane_archive import archive_successful_run
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.time import SystemClock


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


def create_composite_reporter(
    *, pipeline_name: str, manifest_id: str | None, logger: LoggerPort
) -> CompositeRunReportService:
    settings = get_settings()

    def archive(result: RunResult) -> None:
        archive_successful_run(
            result=result,
            options=None,
            data_root=Path(settings.data_dir),
            archive_root=Path(settings.archive_root)
            if settings.archive_root is not None
            else None,
            report_root=settings.report_root,
        )

    return CompositeRunReportService(
        pipeline_name=pipeline_name,
        manifest_id=manifest_id,
        store=FileRunReportStoreAdapter(),
        root=settings.report_root,
        clock=SystemClock(),
        logger=logger,
        archive=archive,
        capture=create_run_status_capture(
            settings.data_dir,
            report_root=settings.report_root,
            archive_root=Path(settings.archive_root)
            if settings.archive_root is not None
            else None,
        ),
    )
