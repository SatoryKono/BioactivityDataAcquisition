"""Planned artifact path helpers for run manifest payloads."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._run_manifest_data_roots import (
    _resolve_data_root,
)
from bioetl.domain.control_plane import RunArtifactRef

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings


def _artifact_path_string(path: Path) -> str:
    """Return portable artifact paths with normalized separators."""
    return path.as_posix()


def build_planned_artifacts(
    *,
    settings: Settings,
    provider: str,
    entity: str,
    run_id: str | None = None,
    pipeline_name: str | None = None,
    workflow_id: str = "standalone",
    debug_export_root: str | None = None,
) -> tuple[RunArtifactRef, ...]:
    """Capture planned layer roots for the manifest control-plane snapshot."""
    output_root = _resolve_data_root(settings) / "output"
    planned = [
        RunArtifactRef(
            layer="bronze",
            path=_artifact_path_string(output_root / "bronze" / provider / entity),
        ),
        RunArtifactRef(
            layer="silver",
            path=_artifact_path_string(output_root / "silver" / provider / entity),
        ),
        RunArtifactRef(
            layer="gold",
            path=_artifact_path_string(output_root / "gold" / provider / entity),
        ),
    ]
    if debug_export_root and run_id and pipeline_name:
        configured_root = Path(debug_export_root)
        if not configured_root.is_absolute():
            configured_root = Path.cwd() / configured_root
        planned.append(
            RunArtifactRef(
                layer="debug_export",
                path=_artifact_path_string(
                    configured_root / workflow_id / pipeline_name / run_id
                ),
            )
        )
    return tuple(planned)
