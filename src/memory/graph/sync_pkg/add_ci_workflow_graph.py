"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import GITHUB_DIR, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.workflow_graph_files import (
    _process_workflow_file,
    _workflow_graph_files,
)

__all__ = [
    "_add_ci_workflow_graph",
]


def _add_ci_workflow_graph(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    workflows_root = root / GITHUB_DIR / "workflows"
    if not workflows_root.is_dir():
        return

    workflow_files = _workflow_graph_files(workflows_root)
    workflow_name_by_relative_path = {
        _rel_path(root, workflow_path): workflow_path.stem
        for workflow_path in workflow_files
    }
    workflow_nodes: dict[str, NodeKey] = {}
    job_nodes: dict[tuple[str, str], NodeKey] = {}
    for workflow_path in workflow_files:
        _process_workflow_file(
            snapshot,
            root,
            project,
            today,
            workflow_path,
            workflow_nodes=workflow_nodes,
            workflow_name_by_relative_path=workflow_name_by_relative_path,
            job_nodes=job_nodes,
        )
