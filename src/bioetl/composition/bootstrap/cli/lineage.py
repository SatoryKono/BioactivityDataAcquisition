"""Bootstrap functions for lineage CLI operations."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageInspectionService,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.control_plane import (
    FileLineageStore,
    FileRunManifestStore,
)

__all__ = ["bootstrap_lineage_service"]


def bootstrap_lineage_service() -> LineageInspectionService:
    """Bootstrap lineage inspection service for CLI commands."""
    settings = get_settings()
    metrics = create_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    return LineageInspectionService(
        lineage_store=FileLineageStore(
            base_path=output_root / "lineage",
            metrics=metrics,
        ),
        manifest_port=FileRunManifestStore(
            base_path=output_root / "run_manifest",
            metrics=metrics,
        ),
    )
