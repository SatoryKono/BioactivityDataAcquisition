"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import WorkflowContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.populate_workflow_job_surface import (
    _populate_workflow_job_surface,
)
from memory.graph.sync_pkg.register_workflow_job import _register_workflow_job
from memory.graph.sync_pkg.workflow_module_script_targets import (
    _add_workflow_job_surface,
)

__all__ = [
    "_process_workflow_job",
]


def _process_workflow_job(
    snapshot: GraphSnapshot,
    *,
    context: WorkflowContext,
    job_id: str,
    job_payload: dict[str, object],
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    workflow_call_entrypoint: NodeKey | None,
    job_nodes: dict[tuple[str, str], NodeKey],
) -> None:
    job_context, matrix_variants, secret_usage_hints = _add_workflow_job_surface(
        snapshot,
        context,
        job_id=job_id,
        job_payload=job_payload,
    )
    _register_workflow_job(
        snapshot,
        context=context,
        job_id=job_id,
        job_context=job_context,
        workflow_call_entrypoint=workflow_call_entrypoint,
        job_nodes=job_nodes,
    )
    _populate_workflow_job_surface(
        snapshot,
        workflow_nodes=workflow_nodes,
        workflow_name_by_relative_path=workflow_name_by_relative_path,
        job_context=job_context,
        job_payload=job_payload,
        matrix_variants=matrix_variants,
        secret_usage_hints=secret_usage_hints,
    )
