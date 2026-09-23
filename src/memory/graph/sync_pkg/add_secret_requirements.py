"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.workflow_matrix_axis_values import _workflow_output_specs

__all__ = [
    "_add_secret_requirements",
    "_add_workflow_output_surface",
    "_add_workflow_outputs",
]


def _add_secret_requirements(
    snapshot: GraphSnapshot,
    owner: NodeKey,
    secret_names: tuple[str, ...],
    *,
    relative_path: str,
    today: str,
) -> None:
    for secret_name in secret_names:
        secret = snapshot.add_node(
            "workflow_secret_surface",
            secret_name,
            summary=f"GitHub Actions secret usage hint `{secret_name}`.",
            source_path=relative_path,
            source_kind="github_actions_secret",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(
            owner, "REQUIRES_SECRET", secret, provenance="workflow_graph"
        )


def _add_workflow_output_surface(
    snapshot: GraphSnapshot,
    *,
    owner: NodeKey,
    output_name: str,
    expression: str | None,
    summary: str,
    relative_path: str,
    workflow_name: str,
    today: str,
    output_scope: str,
    job_id: str | None = None,
) -> None:
    output = snapshot.add_node(
        "workflow_output_surface",
        output_name,
        summary=summary,
        source_path=relative_path,
        source_kind="workflow_output_surface",
        workflow=workflow_name,
        job_id=job_id,
        output_scope=output_scope,
        output_expression=expression,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(owner, "EMITS_OUTPUT", output, provenance="workflow_graph")


def _add_workflow_outputs(
    snapshot: GraphSnapshot,
    *,
    owner: NodeKey,
    workflow_name: str,
    relative_path: str,
    today: str,
    owner_id: str,
    output_payload: object,
    scope: str,
    output_scope: str,
    summary_template: str,
    job_id: str | None = None,
) -> None:
    for output_name, expression in _workflow_output_specs(
        workflow_name,
        owner_id,
        output_payload,
        scope=scope,
    ):
        _add_workflow_output_surface(
            snapshot,
            owner=owner,
            output_name=output_name,
            expression=expression,
            summary=summary_template.format(output_name=output_name),
            relative_path=relative_path,
            workflow_name=workflow_name,
            today=today,
            output_scope=output_scope,
            job_id=job_id,
        )
