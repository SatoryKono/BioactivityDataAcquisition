"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_secret_requirements import _add_workflow_outputs
from memory.graph.sync_pkg.graph_contexts import WorkflowJobContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.workflow_matrix_axis_values import _workflow_action_key

__all__ = [
    "_add_job_matrix_variants",
    "_add_job_outputs",
    "_reusable_target_workflow_key",
]


def _reusable_target_workflow_key(
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    reusable_workflow_ref: str,
    target_workflow_name: str,
) -> NodeKey | None:
    target_key = workflow_nodes.get(target_workflow_name)
    if target_key is not None:
        return target_key
    local_relative_path = _workflow_action_key(reusable_workflow_ref).removeprefix("./")
    target_workflow = workflow_name_by_relative_path.get(local_relative_path)
    if target_workflow is None:
        return None
    return workflow_nodes.get(target_workflow)


def _add_job_matrix_variants(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    matrix_variants: tuple[dict[str, str], ...],
) -> None:
    for variant_payload in matrix_variants:
        variant_name = ", ".join(
            f"{axis}={value}" for axis, value in sorted(variant_payload.items())
        )
        matrix_variant = snapshot.add_node(
            "workflow_matrix_variant_surface",
            f"{context.job_name}[{variant_name}]",
            summary=f"Expanded matrix variant `{variant_name}` for workflow job `{context.job_name}`.",
            source_path=context.relative_path,
            source_kind="workflow_matrix_variant_surface",
            workflow=context.workflow_name,
            job_id=context.job_id,
            variant_axes=variant_payload,
            last_verified=context.today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(
            context.job,
            "HAS_MATRIX_VARIANT",
            matrix_variant,
            provenance="workflow_graph",
        )


def _add_job_outputs(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    output_payload: object,
) -> None:
    _add_workflow_outputs(
        snapshot,
        owner=context.job,
        workflow_name=context.workflow_name,
        relative_path=context.relative_path,
        today=context.today,
        owner_id=context.job_id,
        output_payload=output_payload,
        scope="job_output",
        output_scope="job",
        summary_template="Workflow output `{output_name}`.",
        job_id=context.job_id,
    )
