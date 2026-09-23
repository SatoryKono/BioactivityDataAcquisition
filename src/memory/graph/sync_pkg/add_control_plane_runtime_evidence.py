"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_control_plane_run_instance_surfaces import (
    _add_control_plane_run_instance_surfaces,
)
from memory.graph.sync_pkg.add_runtime_evidence_surface import (
    _add_runtime_evidence_surface,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.runtime_evidence_definitions import (
    _control_plane_runtime_evidence_specs,
)

__all__ = [
    "_add_control_plane_runtime_evidence",
]


def _add_control_plane_runtime_evidence(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> None:
    for spec in _control_plane_runtime_evidence_specs():
        _add_runtime_evidence_surface(snapshot, project, today, spec)

    _add_control_plane_run_instance_surfaces(snapshot, root, project, today)
