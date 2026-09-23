"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_runtime_evidence_surface import (
    _link_run_instance_surface,
)
from memory.graph.sync_pkg.add_runtime_state_spec_surfaces import (
    _add_runtime_state_spec_surfaces,
)
from memory.graph.sync_pkg.add_secret_requirements import _add_secret_requirements
from memory.graph.sync_pkg.graph_contexts import WorkflowJobContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_runtime_evidence_support import (
    _add_run_instance_surface,
)
from memory.graph.sync_pkg.link_workflow_run_targets import _link_workflow_run_targets
from memory.graph.sync_pkg.process_workflow_uses_step import _process_workflow_uses_step
from memory.graph.sync_pkg.runtime_evidence_storage_refs import (
    _control_plane_run_instance_specs,
)
from memory.graph.sync_pkg.workflow_matrix_axis_values import _workflow_secret_refs

__all__ = [
    "_add_run_instance_spec_surfaces",
    "_add_runtime_state_surfaces",
    "_process_workflow_steps",
]


def _add_run_instance_spec_surfaces(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
) -> None:
    for spec in _control_plane_run_instance_specs():
        surface = _add_run_instance_surface(snapshot, project, today, spec)
        _link_run_instance_surface(snapshot, surface, spec)


def _add_runtime_state_surfaces(
    snapshot: GraphSnapshot, project: NodeKey, today: str
) -> None:
    _add_runtime_state_spec_surfaces(snapshot, project, today)


def _process_workflow_steps(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    steps: object,
) -> None:
    if not isinstance(steps, list):
        return
    for step in steps:
        if not isinstance(step, dict):
            continue
        uses_ref = step.get("uses")
        if isinstance(uses_ref, str):
            _process_workflow_uses_step(snapshot, context, uses_ref, step)
        run_text = step.get("run")
        if not isinstance(run_text, str):
            continue
        _link_workflow_run_targets(snapshot, context, run_text)
        _add_secret_requirements(
            snapshot,
            context.job,
            _workflow_secret_refs(step),
            relative_path=context.relative_path,
            today=context.today,
        )
