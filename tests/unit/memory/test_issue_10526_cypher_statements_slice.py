"""Ratchet and unit coverage for AUD-002 Cypher builder extract (#10526)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.graph.sync_pkg import _core
from memory.graph.sync_pkg import neo4j_statements as statements
from memory.graph.sync_pkg._core_models import NodeKey

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "_core.py"
STMTS = ROOT / "src" / "memory" / "graph" / "sync_pkg" / "neo4j_statements.py"
# Line count after the AST slice (#10639).
_CORE_LOC_BEFORE_CYPHER_SLICE = 17261


def _loc(path: Path) -> int:
    return path.read_text(encoding="utf-8").count("\n") + 1


def test_cypher_builders_own_statements_and_shrink_core() -> None:
    core_text = CORE.read_text(encoding="utf-8")
    stmt_text = STMTS.read_text(encoding="utf-8")
    assert "def _node_statement(" not in core_text
    assert "def _neo4j_property_value(" not in core_text
    assert "def _node_statement(" in stmt_text
    assert _core._node_statement is statements._node_statement
    assert _core.DEFAULT_MANAGED_BY == statements.DEFAULT_MANAGED_BY
    core_loc = _loc(CORE)
    stmt_loc = _loc(STMTS)
    assert core_loc < _CORE_LOC_BEFORE_CYPHER_SLICE
    assert stmt_loc < 500


def test_node_and_relation_statements_embed_managed_properties() -> None:
    node = _core.GraphNode(
        key=NodeKey(label="module_surface", name="src/example.py"),
        properties={"role": "kernel", "tags": ["a", "b"]},
    )
    payload = statements._node_statement(node, "run-1")
    assert "MERGE (n:`module_surface`" in str(payload["statement"])
    props = payload["parameters"]["properties"]
    assert isinstance(props, dict)
    assert props["managed_by"] == statements.DEFAULT_MANAGED_BY
    assert props["sync_run"] == "run-1"
    assert props["ingest_wave"] == statements.DEFAULT_INGEST_WAVE
    assert props["tags"] == ["a", "b"]

    relation = _core.GraphRelation(
        source=node.key,
        relation_type="IMPORTS",
        target=NodeKey(label="module_surface", name="src/other.py"),
        properties={"nested": {"k": 1}},
    )
    rel_payload = statements._relation_statement(relation, "run-1")
    rel_props = rel_payload["parameters"]["properties"]
    assert isinstance(rel_props, dict)
    assert rel_props["nested"] == '{"k": 1}'
    assert "MERGE (a)-[r:`IMPORTS`]->(b)" in str(rel_payload["statement"])


def test_prune_and_reset_statements_bind_wave_constants() -> None:
    reset = statements._reset_managed_relations_statement(["IMPORTS"])
    assert reset["parameters"]["relation_types"] == ["IMPORTS"]
    assert reset["parameters"]["managed_by"] == statements.DEFAULT_MANAGED_BY
    prune_rel = statements._prune_stale_relations_statement("run-2")
    assert prune_rel["parameters"]["sync_run"] == "run-2"
    prune_nodes = statements._prune_stale_nodes_statement("run-2")
    assert "DETACH DELETE n" in str(prune_nodes["statement"])
    delete_wave = statements._delete_managed_wave_nodes_statement("module_surface", 50)
    assert delete_wave["parameters"]["limit"] == 50
    legacy = statements._prune_legacy_unmanaged_nodes_statement(["module_surface"])
    assert legacy["parameters"]["managed_labels"] == ["module_surface"]
