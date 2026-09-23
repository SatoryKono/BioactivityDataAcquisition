"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import json
from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.curated_quality_gates import CURATED_QUALITY_GATES
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _read_json

__all__ = [
    "_add_curated_quality_gates",
    "_add_dashboard_surface",
    "_add_execution_path_node",
    "_developer_workflow_readme",
    "_link_execution_gate",
]


def _add_dashboard_surface(
    snapshot: GraphSnapshot,
    root: Path,
    dashboard_path: Path,
    today: str,
) -> NodeKey:
    name = dashboard_path.stem
    try:
        payload = _read_json(dashboard_path)
    except (OSError, json.JSONDecodeError):
        payload = {}
    title = payload.get("title") if isinstance(payload.get("title"), str) else None
    return snapshot.add_node(
        "dashboard_surface",
        name,
        summary=str(title or f"Grafana dashboard `{name}`."),
        source_path=_rel_path(root, dashboard_path),
        source_kind="dashboard_json",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _add_curated_quality_gates(
    snapshot: GraphSnapshot, project: NodeKey, today: str
) -> None:
    for gate_payload in CURATED_QUALITY_GATES:
        gate = snapshot.add_node(
            "quality_gate",
            str(gate_payload["name"]),
            summary=str(gate_payload["summary"]),
            source_kind="curated_quality_gate",
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(
            project, "HAS_QUALITY_GATE", gate, provenance="curated_quality"
        )


def _developer_workflow_readme(
    snapshot: GraphSnapshot, project: NodeKey, today: str
) -> NodeKey:
    dev_readme = snapshot.add_node(
        "doc_artifact",
        "scripts/engineering/dev/README.md",
        summary="Developer workflow and wrapper entrypoint guide.",
        source_path="scripts/engineering/dev/README.md",
        source_kind="ops_doc",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_DOC_ARTIFACT", dev_readme, provenance="curated_scripts"
    )
    return dev_readme


def _add_execution_path_node(
    snapshot: GraphSnapshot,
    today: str,
    execution_payload: dict[str, object],
) -> NodeKey:
    return snapshot.add_node(
        "execution_path",
        str(execution_payload["name"]),
        summary=str(execution_payload["summary"]),
        platform=str(execution_payload["platform"]),
        source_kind="execution_path",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _link_execution_gate(
    snapshot: GraphSnapshot,
    execution: NodeKey,
    execution_payload: dict[str, object],
    *,
    provenance: str,
) -> None:
    gate_name = execution_payload.get("gate")
    if isinstance(gate_name, str):
        snapshot.add_relation(
            execution,
            "EXECUTES_GATE",
            NodeKey("quality_gate", gate_name),
            provenance=provenance,
        )
