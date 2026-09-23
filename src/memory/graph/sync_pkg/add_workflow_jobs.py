"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import WorkflowContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_workflow_job_dependencies import (
    _link_workflow_job_dependencies,
)
from memory.graph.sync_pkg.process_workflow_job import _process_workflow_job

__all__ = [
    "_add_workflow_jobs",
]


def _add_workflow_jobs(
    snapshot: GraphSnapshot,
    *,
    context: WorkflowContext,
    jobs: dict[object, object],
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    workflow_call_entrypoint: NodeKey | None,
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    for job_id, job_payload in jobs.items():
        if not isinstance(job_payload, dict):
            continue
        _process_workflow_job(
            snapshot,
            context=context,
            job_id=str(job_id),
            job_payload=job_payload,
            workflow_nodes=workflow_nodes,
            workflow_name_by_relative_path=workflow_name_by_relative_path,
            workflow_call_entrypoint=workflow_call_entrypoint,
            job_nodes=job_nodes,
        )
    _link_workflow_job_dependencies(
        snapshot,
        context.workflow_name,
        {str(key): value for key, value in jobs.items()},
        job_nodes,
    )
