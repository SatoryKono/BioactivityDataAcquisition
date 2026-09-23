"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _normalize_cli_command_name
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_cli_command_surface import (
    _add_cli_command_surface,
    _add_cli_option_surfaces,
    _cli_command_source_path,
    _cli_execution_indexes,
    _link_cli_command_execution,
    _link_cli_command_side_effects,
)
from memory.graph.sync_pkg.add_dashboard_surface import (
    _add_curated_quality_gates,
    _add_execution_path_node,
    _developer_workflow_readme,
    _link_execution_gate,
)
from memory.graph.sync_pkg.composite_dependency_target import (
    _composite_dependency_target,
)
from memory.graph.sync_pkg.curated_quality_gates import CURATED_EXECUTION_PATHS
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_curated_execution_script import (
    _add_curated_script_clusters,
    _link_curated_execution_script,
)
from memory.graph.sync_pkg.workflow_output_expression import _extract_cli_options

__all__ = [
    "_add_cli_command_graph",
    "_add_curated_execution_paths",
    "_add_quality_and_scripts",
    "_composite_config_dependency_entries",
    "_link_composite_dependency",
    "_link_composite_seed_dependency",
]


def _composite_config_dependency_entries(
    composite_payload: object,
) -> tuple[object, ...]:
    dependencies = (
        composite_payload.get("dependencies")
        if isinstance(composite_payload, dict)
        else None
    )
    if not isinstance(dependencies, list):
        return ()
    return tuple(dependencies)


def _link_composite_seed_dependency(
    snapshot: GraphSnapshot,
    composite_node: NodeKey,
    *,
    seed_pipeline: str | None,
    entity_nodes: dict[str, NodeKey],
) -> None:
    target = _composite_dependency_target(seed_pipeline, entity_nodes)
    if target is not None:
        snapshot.add_relation(
            composite_node, "DEPENDS_ON", target, provenance="composite_seed"
        )


def _link_composite_dependency(
    snapshot: GraphSnapshot,
    composite_node: NodeKey,
    dependency: object,
    entity_nodes: dict[str, NodeKey],
) -> None:
    if not isinstance(dependency, dict):
        return
    target = _composite_dependency_target(dependency.get("pipeline"), entity_nodes)
    if target is not None:
        snapshot.add_relation(
            composite_node,
            "DEPENDS_ON",
            target,
            provenance="composite_dependency",
            required=bool(dependency.get("required", False)),
        )


def _add_curated_execution_paths(
    snapshot: GraphSnapshot, today: str, dev_readme: NodeKey
) -> None:
    for execution_payload in CURATED_EXECUTION_PATHS:
        execution = _add_execution_path_node(snapshot, today, execution_payload)
        _link_execution_gate(
            snapshot, execution, execution_payload, provenance="curated_execution"
        )
        _link_curated_execution_script(
            snapshot, execution, execution_payload, today=today, dev_readme=dev_readme
        )


def _add_quality_and_scripts(
    snapshot: GraphSnapshot, _root: Path, project: NodeKey, today: str
) -> None:
    _add_curated_quality_gates(snapshot, project, today)
    dev_readme = _developer_workflow_readme(snapshot, project, today)
    _add_curated_execution_paths(snapshot, today, dev_readme)
    _add_curated_script_clusters(snapshot, project, today)


def _add_cli_command_graph(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    execution_to_gates, execution_to_scripts = _cli_execution_indexes(snapshot)
    for execution in tuple(snapshot.nodes.values()):
        if execution.key.label != "execution_path":
            continue
        command_name = _normalize_cli_command_name(execution.key.name)
        if command_name is None:
            continue
        backing_scripts = execution_to_scripts.get(execution.key, [])
        source_path = _cli_command_source_path(root, command_name, backing_scripts)
        command_options = _extract_cli_options(execution.key.name)
        command = _add_cli_command_surface(
            snapshot,
            execution,
            command_name=command_name,
            source_path=source_path,
            command_options=command_options,
            today=today,
        )
        snapshot.add_relation(
            project, "HAS_CLI_COMMAND", command, provenance="cli_command_graph"
        )
        _link_cli_command_execution(
            snapshot,
            command,
            execution.key,
            execution_to_gates.get(execution.key, []),
            backing_scripts,
        )
        _add_cli_option_surfaces(
            snapshot,
            command,
            command_name=command_name,
            source_path=source_path,
            command_options=command_options,
            today=today,
        )
        _link_cli_command_side_effects(snapshot, command, command_name)
