"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _is_ignored_repo_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.process_adapter_module import _process_adapter_module
from memory.graph.sync_pkg.process_adapter_package import _process_adapter_package
from memory.graph.sync_pkg.python_paths import INIT_PY

__all__ = [
    "_process_adapter_root_child",
]


def _process_adapter_root_child(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    child: Path,
    *,
    adapter_family: NodeKey,
    adapter_nodes: dict[str, NodeKey],
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
    port_names: set[str],
    fine_grained_enabled: bool,
) -> None:
    if _is_ignored_repo_path(child) or child.name.startswith("_"):
        return
    if child.is_dir():
        _process_adapter_package(
            snapshot,
            root,
            project,
            today,
            child,
            adapter_family=adapter_family,
            adapter_nodes=adapter_nodes,
            port_module_surfaces=port_module_surfaces,
            port_symbol_index=port_symbol_index,
            port_names=port_names,
            fine_grained_enabled=fine_grained_enabled,
        )
        return
    if child.suffix != ".py" or child.name == INIT_PY:
        return
    _process_adapter_module(
        snapshot,
        root,
        project,
        today,
        child,
        adapter_family=adapter_family,
        adapter_nodes=adapter_nodes,
        port_module_surfaces=port_module_surfaces,
        port_symbol_index=port_symbol_index,
        port_names=port_names,
    )
