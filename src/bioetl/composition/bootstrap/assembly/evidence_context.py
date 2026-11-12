"""Assemble validation ports for one explicitly selected evidence root."""

from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
)
from bioetl.application.services.run_reports.paths import resolve_report_root
from bioetl.domain.ports import MetricsPort, RawRunManifestInspectionPort
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)
from bioetl.infrastructure.control_plane.file_evidence_read_context import (
    FileEvidenceReadContext,
    _SelectedRootLedgerPort,
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
    validation_service = ControlPlaneEvidenceService(
        ledger_port=_SelectedRootLedgerPort(context),
        lineage_store=context.lineage_port,
        manifest_inspector=manifest_inspector,
        lifecycle_planner=FileControlPlaneArtifactLifecycleStore(
            base_path=output_root, metrics=metrics
        ),
        archive_verifier=archive_verifier,
    )
    return replace(context, validation_service=validation_service)
