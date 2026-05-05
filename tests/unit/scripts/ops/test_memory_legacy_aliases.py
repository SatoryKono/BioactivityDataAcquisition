from __future__ import annotations

import importlib


def test_scripts_memory_sync_is_canonical_module_alias() -> None:
    legacy = importlib.import_module("scripts.memory.sync")
    canonical = importlib.import_module("memory.graph.sync")
    assert legacy is canonical


def test_scripts_ops_neo4j_memory_sync_is_canonical_module_alias() -> None:
    legacy = importlib.import_module("scripts.ops.neo4j_memory_sync")
    canonical = importlib.import_module("memory.graph.sync")
    assert legacy is canonical


def test_scripts_memory_query_is_canonical_module_alias() -> None:
    legacy = importlib.import_module("scripts.memory.query")
    canonical = importlib.import_module("memory.graph.query")
    assert legacy is canonical
