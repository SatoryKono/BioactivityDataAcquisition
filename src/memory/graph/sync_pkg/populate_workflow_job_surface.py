"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_run_instance_spec_surfaces import _process_workflow_steps
from memory.graph.sync_pkg.add_secret_requirements import _add_secret_requirements
from memory.graph.sync_pkg.alert_rule_file_payload import (
    _link_workflow_job_reusable_target,
)
from memory.graph.sync_pkg.graph_contexts import WorkflowJobContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.reusable_target_workflow_key import (
    _add_job_matrix_variants,
    _add_job_outputs,
)

__all__ = [
    "_populate_workflow_job_surface",
]


def _populate_workflow_job_surface(
    snapshot: GraphSnapshot,
    *,
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    job_context: WorkflowJobContext,
    job_payload: dict[str, object],
    matrix_variants: tuple[dict[str, str], ...],
    secret_usage_hints: tuple[str, ...],
) -> None:
    _link_workflow_job_reusable_target(
        snapshot,
        workflow_nodes,
        workflow_name_by_relative_path,
        job_context,
        job_payload.get("uses"),
    )
    _add_secret_requirements(
        snapshot,
        job_context.job,
        secret_usage_hints,
        relative_path=job_context.relative_path,
        today=job_context.today,
    )
    _add_job_matrix_variants(snapshot, job_context, matrix_variants)
    _add_job_outputs(snapshot, job_context, job_payload.get("outputs"))
    _process_workflow_steps(snapshot, job_context, job_payload.get("steps"))
