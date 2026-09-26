"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_run_instance_dependencies import (
    _add_runtime_state_surface,
)
from memory.graph.sync_pkg.link_runtime_state_surface import _link_runtime_state_surface
from memory.graph.sync_pkg.run_instance_doc_targets import _runtime_state_specs
from memory.graph.sync_pkg.workflow_module_script_targets import (
    _workflow_module_script_targets,
    _workflow_repo_path_targets,
)

__all__ = [
    "_add_runtime_state_spec_surfaces",
    "_workflow_script_targets",
]


def _add_runtime_state_spec_surfaces(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
) -> None:
    for spec in _runtime_state_specs():
        state = _add_runtime_state_surface(snapshot, project, today, spec)
        _link_runtime_state_surface(snapshot, state, spec)


def _workflow_script_targets(run_text: str) -> set[NodeKey]:
    targets: set[NodeKey] = set()
    targets.update(_workflow_module_script_targets(run_text))
    targets.update(_workflow_repo_path_targets(run_text))
    return targets
