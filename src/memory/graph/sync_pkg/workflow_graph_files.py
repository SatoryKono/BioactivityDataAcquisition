"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_workflow_file_surface import _add_workflow_file_surface
from memory.graph.sync_pkg.add_workflow_jobs import _add_workflow_jobs
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_process_workflow_file",
    "_workflow_graph_files",
]


def _workflow_graph_files(workflows_root: Path) -> list[Path]:
    return sorted(workflows_root.glob("*.y*ml"))


def _process_workflow_file(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    workflow_path: Path,
    *,
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    workflow_name, payload, context, workflow_call_entrypoint = (
        _add_workflow_file_surface(
            snapshot,
            root,
            project,
            today,
            workflow_path,
        )
    )
    workflow_nodes[workflow_name] = context.workflow
    jobs = payload.get("jobs")
    if not isinstance(jobs, dict):
        return
    _add_workflow_jobs(
        snapshot,
        context=context,
        jobs=jobs,
        workflow_nodes=workflow_nodes,
        workflow_name_by_relative_path=workflow_name_by_relative_path,
        workflow_call_entrypoint=workflow_call_entrypoint,
        job_nodes=job_nodes,
    )
