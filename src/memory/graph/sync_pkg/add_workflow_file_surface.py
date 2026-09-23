"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.contains_any import (
    _add_workflow_call_entrypoint,
    _enrich_workflow_surface,
)
from memory.graph.sync_pkg.graph_contexts import WorkflowContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _read_yaml
from memory.graph.sync_pkg.workflow_matrix_axis_values import (
    _attach_workflow_file_backing,
)
from memory.graph.sync_pkg.workflow_output_expression import _add_workflow_surface

__all__ = [
    "_add_workflow_file_surface",
]


def _add_workflow_file_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    workflow_path: Path,
) -> tuple[str, dict[str, object], WorkflowContext, NodeKey | None]:
    payload = _read_yaml(workflow_path)
    workflow_name = workflow_path.stem
    title_value = payload.get("name")
    title = title_value if isinstance(title_value, str) else workflow_name
    relative_path = _rel_path(root, workflow_path)
    context = _add_workflow_surface(
        snapshot,
        workflow_name=workflow_name,
        title=title,
        relative_path=relative_path,
        today=today,
    )
    _enrich_workflow_surface(snapshot, context, payload)
    snapshot.add_relation(
        project, "HAS_WORKFLOW", context.workflow, provenance="workflow_graph"
    )
    _attach_workflow_file_backing(snapshot, context.workflow, relative_path)
    workflow_call_entrypoint = _add_workflow_call_entrypoint(snapshot, context, payload)
    return workflow_name, payload, context, workflow_call_entrypoint
