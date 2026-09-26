"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import GATE_NEO4J_ONTOLOGY_INVARIANTS
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot
from memory.graph.sync_pkg.workflow_output_expression import _cli_side_effect_class

__all__ = [
    "_add_cli_command_surface",
    "_add_cli_option_surfaces",
    "_cli_command_source_path",
    "_cli_execution_indexes",
    "_link_cli_command_execution",
    "_link_cli_command_side_effects",
]


def _add_cli_command_surface(
    snapshot: GraphSnapshot,
    execution: GraphNode,
    *,
    command_name: str,
    source_path: str | None,
    command_options: tuple[str, ...],
    today: str,
) -> NodeKey:
    return snapshot.add_node(
        "cli_command_surface",
        command_name,
        summary=f"CLI command surface `{command_name}`.",
        source_path=source_path,
        source_kind="cli_command_surface",
        platform=str(execution.properties.get("platform") or ""),
        side_effect_class=_cli_side_effect_class(command_name),
        command_options=list(command_options) if command_options else None,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _link_cli_command_execution(
    snapshot: GraphSnapshot,
    command: NodeKey,
    execution_key: NodeKey,
    gates: list[NodeKey],
    scripts: list[NodeKey],
) -> None:
    snapshot.add_relation(
        command, "RUNS_VIA", execution_key, provenance="cli_command_graph"
    )
    for gate in gates:
        snapshot.add_relation(
            command, "EXECUTES_GATE", gate, provenance="cli_command_graph"
        )
    for script in scripts:
        snapshot.add_relation(
            command, "DEPENDS_ON", script, provenance="cli_command_graph"
        )


def _cli_execution_indexes(
    snapshot: GraphSnapshot,
) -> tuple[dict[NodeKey, list[NodeKey]], dict[NodeKey, list[NodeKey]]]:
    execution_to_gates: dict[NodeKey, list[NodeKey]] = {}
    execution_to_scripts: dict[NodeKey, list[NodeKey]] = {}
    for relation in snapshot.relations.values():
        if (
            relation.source.label == "execution_path"
            and relation.relation_type == "EXECUTES_GATE"
        ):
            execution_to_gates.setdefault(relation.source, []).append(relation.target)
        if (
            relation.target.label == "execution_path"
            and relation.relation_type == "PROVIDES"
        ):
            execution_to_scripts.setdefault(relation.target, []).append(relation.source)
    return execution_to_gates, execution_to_scripts


def _cli_command_source_path(
    root: Path,
    command_name: str,
    backing_scripts: list[NodeKey],
) -> str | None:
    if backing_scripts:
        return backing_scripts[0].name
    if command_name.startswith("bioetl "):
        command_suffix = command_name.split(" ", 1)[1]
        source_candidate = (
            root
            / "src/bioetl/interfaces/cli/commands"
            / f"{command_suffix.replace('-', '_')}.py"
        )
        if source_candidate.is_file():
            return _rel_path(root, source_candidate)
    return None


def _add_cli_option_surfaces(
    snapshot: GraphSnapshot,
    command: NodeKey,
    *,
    command_name: str,
    source_path: str | None,
    command_options: tuple[str, ...],
    today: str,
) -> None:
    for option_name in command_options:
        option = snapshot.add_node(
            "cli_option_surface",
            f"{command_name} {option_name}",
            summary=f"Observed CLI option `{option_name}` for command `{command_name}`.",
            source_path=source_path,
            source_kind="cli_option_surface",
            command=command_name,
            option_name=option_name,
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="medium",
        )
        snapshot.add_relation(
            command, "ACCEPTS_OPTION", option, provenance="cli_command_graph"
        )


def _link_cli_command_side_effects(
    snapshot: GraphSnapshot,
    command: NodeKey,
    command_name: str,
) -> None:
    if command_name == "bioetl run":
        for target in sorted(
            (key for key in snapshot.nodes if key.label == "pipeline_surface"),
            key=lambda key: key.name,
        )[:5]:
            snapshot.add_relation(
                command, "SIDE_EFFECTS_ON", target, provenance="cli_command_graph"
            )
        return
    if command_name == "scripts.memory sync":
        gate_key = NodeKey("quality_gate", GATE_NEO4J_ONTOLOGY_INVARIANTS)
        if gate_key in snapshot.nodes:
            snapshot.add_relation(
                command, "SIDE_EFFECTS_ON", gate_key, provenance="cli_command_graph"
            )
