"""Bootstrap control-plane lifecycle stores for CLI commands."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.control_plane import FileControlPlaneArtifactLifecycleStore
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

__all__ = ["bootstrap_control_plane_lifecycle_store"]


def bootstrap_control_plane_lifecycle_store() -> FileControlPlaneArtifactLifecycleStore:
    """Build the file-backed lifecycle store for CLI operations."""
    settings = get_settings()
    output_root = Path(settings.data_dir) / "output"
    return FileControlPlaneArtifactLifecycleStore(
        base_path=output_root / "control",
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
    )
