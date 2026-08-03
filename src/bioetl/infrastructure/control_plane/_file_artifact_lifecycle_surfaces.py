"""Surface file iteration helpers for control-plane lifecycle planning."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.control_plane import ControlPlaneArtifactSurface

INDEX_DIR_NAMES = {
    "_by_fragment_id",
    "_by_manifest_id",
    "_by_node_id",
    "_by_run_id",
    "_occurrences",
}


def iter_surface_files(
    base_path: Path,
    surface: ControlPlaneArtifactSurface,
) -> tuple[Path, ...]:
    surface_root = surface_root_path(base_path, surface)
    if not surface_root.exists():
        return ()
    return tuple(path for path in surface_root.rglob("*") if path.is_file())


def surface_root_path(base_path: Path, surface: ControlPlaneArtifactSurface) -> Path:
    if surface in {
        ControlPlaneArtifactSurface.CACHED_BRONZE,
        ControlPlaneArtifactSurface.CHECKPOINT,
    }:
        return base_path.parent / surface.value
    return base_path / surface.value


def lineage_fragment_files(base_path: Path) -> tuple[Path, ...]:
    fragments_root = base_path / ControlPlaneArtifactSurface.LINEAGE / "fragments"
    if not fragments_root.exists():
        return ()
    return tuple(path for path in fragments_root.glob("*.json") if path.is_file())
