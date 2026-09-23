"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import WorkflowContext, WorkflowJobContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.reusable_target_workflow_key import (
    _reusable_target_workflow_key,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _workflow_action_key,
    _workflow_reusable_target,
)

__all__ = [
    "_add_workflow_action_surface",
    "_create_workflow_job_surface",
    "_link_reusable_job_workflow",
]


def _create_workflow_job_surface(
    snapshot: GraphSnapshot,
    context: WorkflowContext,
    *,
    job_name: str,
    job_id: str,
    job_payload: dict[str, object],
    inline_run_step_count: int,
    uses_step_count: int,
    matrix_axes: tuple[str, ...],
    matrix_variants: tuple[dict[str, str], ...],
    environment_name: str | None,
    secret_usage_hints: tuple[str, ...],
    concurrency_group: str | None,
) -> NodeKey:
    return snapshot.add_node(
        "workflow_job_surface",
        job_name,
        summary=f"GitHub Actions job `{job_id}` in workflow `{context.title}`.",
        source_path=context.relative_path,
        source_kind="github_actions_job",
        workflow=context.workflow_name,
        job_id=job_id,
        runs_on=str(job_payload.get("runs-on"))
        if job_payload.get("runs-on") is not None
        else None,
        inline_run_step_count=inline_run_step_count,
        uses_step_count=uses_step_count,
        matrix_axes=list(matrix_axes) if matrix_axes else None,
        matrix_variant_count=len(matrix_variants) if matrix_variants else None,
        environment_name=environment_name,
        secret_usage_hints=list(secret_usage_hints) if secret_usage_hints else None,
        concurrency_group=concurrency_group,
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_workflow_action_surface(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    *,
    action_key: str,
    uses_ref: str,
    summary: str,
) -> NodeKey:
    action = snapshot.add_node(
        "workflow_action_surface",
        action_key,
        summary=summary,
        source_path=context.relative_path,
        source_kind="github_actions_uses",
        uses_ref=uses_ref,
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        context.job, "USES_ACTION", action, provenance="workflow_graph"
    )
    return action


def _link_reusable_job_workflow(
    snapshot: GraphSnapshot,
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    context: WorkflowJobContext,
    reusable_workflow_ref: str,
) -> None:
    action_key = _workflow_action_key(reusable_workflow_ref)
    target_workflow_name, reusable_kind = _workflow_reusable_target(
        reusable_workflow_ref
    )
    _add_workflow_action_surface(
        snapshot,
        context,
        action_key=action_key,
        uses_ref=reusable_workflow_ref,
        summary=f"Workflow action or reusable workflow `{action_key}`.",
    )
    if target_workflow_name is None:
        return
    workflow_call = snapshot.add_node(
        "workflow_call_surface",
        f"{context.job_name}::{action_key}",
        summary=f"Reusable workflow call `{action_key}` from job `{context.job_name}`.",
        source_path=context.relative_path,
        source_kind="workflow_call_surface",
        workflow=context.workflow_name,
        job_id=context.job_id,
        uses_ref=reusable_workflow_ref,
        reusable_kind=reusable_kind,
        target_workflow=target_workflow_name,
        last_verified=context.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        context.job, "CALLS_WORKFLOW", workflow_call, provenance="workflow_graph"
    )
    target_key = _reusable_target_workflow_key(
        workflow_nodes,
        workflow_name_by_relative_path,
        reusable_workflow_ref,
        target_workflow_name,
    )
    if target_key is not None:
        snapshot.add_relation(
            workflow_call, "DEPENDS_ON", target_key, provenance="workflow_graph"
        )
