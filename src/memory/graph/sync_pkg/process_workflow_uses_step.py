"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg.create_workflow_job_surface import (
    _add_workflow_action_surface,
)
from memory.graph.sync_pkg.graph_contexts import WorkflowJobContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.workflow_matrix_axis_values import _workflow_action_key
from memory.graph.sync_pkg.workflow_output_expression import _workflow_artifact_specs

__all__ = [
    "_process_workflow_uses_step",
]


def _process_workflow_uses_step(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    uses_ref: str,
    step: dict[str, object],
) -> None:
    action_key = _workflow_action_key(uses_ref)
    _add_workflow_action_surface(
        snapshot,
        context,
        action_key=action_key,
        uses_ref=uses_ref,
        summary=f"Workflow action `{action_key}`.",
    )
    for artifact_name, artifact_relation, artifact_path in _workflow_artifact_specs(
        context.workflow_name,
        context.job_id,
        step,
    ):
        artifact = snapshot.add_node(
            "workflow_artifact_surface",
            artifact_name,
            summary=f"Workflow artifact `{artifact_name}`.",
            source_path=context.relative_path,
            source_kind="github_actions_artifact",
            artifact_path=artifact_path,
            workflow=context.workflow_name,
            last_verified=context.today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(
            context.job, artifact_relation, artifact, provenance="workflow_graph"
        )
