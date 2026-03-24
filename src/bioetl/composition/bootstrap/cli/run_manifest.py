"""Bootstrap functions for run-manifest CLI operations."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.infrastructure.config import get_settings
from bioetl.infrastructure.control_plane import (
    FileRunLedgerStore,
    FileRunManifestStore,
)

__all__ = ["bootstrap_run_manifest_service"]


def bootstrap_run_manifest_service() -> RunManifestInspectionService:
    """Bootstrap manifest/ledger inspection service for CLI commands."""
    settings = get_settings()
    output_root = Path(settings.data_dir) / "output" / "control"
    return RunManifestInspectionService(
        manifest_port=FileRunManifestStore(base_path=output_root / "run_manifest"),
        ledger_port=FileRunLedgerStore(base_path=output_root / "run_ledger"),
    )
