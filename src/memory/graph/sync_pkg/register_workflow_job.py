"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import WorkflowContext, WorkflowJobContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_register_workflow_job",
]


def _register_workflow_job(
    snapshot: GraphSnapshot,
    *,
    context: WorkflowContext,
    job_id: str,
    job_context: WorkflowJobContext,
    workflow_call_entrypoint: NodeKey | None,
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    job_nodes[(context.workflow_name, job_id)] = job_context.job
    if workflow_call_entrypoint is not None:
        snapshot.add_relation(
            job_context.job,
            "CALLS_WORKFLOW",
            workflow_call_entrypoint,
            provenance="workflow_graph",
        )
