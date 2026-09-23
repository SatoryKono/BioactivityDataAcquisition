"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_runtime_state_spec_surfaces import (
    _workflow_script_targets,
)
from memory.graph.sync_pkg.graph_contexts import WorkflowJobContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.workflow_module_script_targets import _workflow_quality_gates

__all__ = [
    "_link_workflow_run_targets",
]


def _link_workflow_run_targets(
    snapshot: GraphSnapshot,
    context: WorkflowJobContext,
    run_text: str,
) -> None:
    for target in sorted(
        _workflow_script_targets(run_text), key=lambda item: (item.label, item.name)
    ):
        if target in snapshot.nodes:
            snapshot.add_relation(
                context.job, "RUNS_VIA", target, provenance="workflow_graph"
            )
    for gate_name in _workflow_quality_gates(run_text):
        gate_key = NodeKey("quality_gate", gate_name)
        if gate_key in snapshot.nodes:
            snapshot.add_relation(
                context.job, "EXECUTES_GATE", gate_key, provenance="workflow_graph"
            )
