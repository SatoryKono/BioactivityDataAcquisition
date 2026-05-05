"""Bootstrap functions for run-manifest CLI operations."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.services.control_plane.forensic_diff_service import (
    ForensicRunDiffService,
)
from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.control_plane import (
    FileArtifactByteComparisonAdapter,
    FileEffectiveConfigArtifactStore,
    FileRunLedgerStore,
    FileRunManifestStore,
)

__all__ = ["bootstrap_forensic_run_diff_service", "bootstrap_run_manifest_service"]


def _create_control_plane_stores() -> tuple[
    FileRunManifestStore,
    FileRunLedgerStore,
    FileEffectiveConfigArtifactStore,
]:
    """Create file-backed control-plane stores for CLI inspection services."""
    settings = get_settings()
    metrics = create_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    return (
        FileRunManifestStore(
            base_path=output_root / "run_manifest",
            metrics=metrics,
        ),
        FileRunLedgerStore(
            base_path=output_root / "run_ledger",
            metrics=metrics,
        ),
        FileEffectiveConfigArtifactStore(
            base_path=output_root / "effective_config",
        ),
    )


def bootstrap_run_manifest_service() -> RunManifestInspectionService:
    """Bootstrap manifest/ledger inspection service for CLI commands."""
    manifest_store, ledger_store, effective_config_store = (
        _create_control_plane_stores()
    )
    return RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        effective_config_artifact_port=effective_config_store,
    )


def bootstrap_forensic_run_diff_service() -> ForensicRunDiffService:
    """Bootstrap unified forensic run-diff service for CLI diagnostics."""
    manifest_store, ledger_store, effective_config_store = (
        _create_control_plane_stores()
    )
    return ForensicRunDiffService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        artifact_byte_comparison_port=FileArtifactByteComparisonAdapter(),
        inspection_service_factory=lambda: RunManifestInspectionService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            effective_config_artifact_port=effective_config_store,
        ),
    )
