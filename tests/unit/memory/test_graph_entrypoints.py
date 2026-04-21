"""Tests for canonical ``memory.graph`` entrypoints."""

from __future__ import annotations

from pathlib import Path

import yaml

from memory.graph import __main__ as graph_main
from memory.graph import query as graph_query
from memory.graph import sync as graph_sync


def test_graph_sync_facade_exposes_legacy_symbols() -> None:
    assert graph_sync.DEFAULT_INGEST_WAVE == "repo_sync_v1"
    assert callable(graph_sync.build_snapshot)


def test_graph_query_facade_exposes_legacy_symbols() -> None:
    assert "owner-pipeline" in graph_query.QUERY_PROFILES
    assert callable(graph_query.main)


def test_graph_sync_uses_repo_root_from_src_layout() -> None:
    assert (graph_sync.DEFAULT_ROOT / "src" / "bioetl").exists()


def test_graph_query_uses_native_sync_module() -> None:
    assert graph_query.resolve_neo4j_connection.__module__ == "memory.graph.sync"


def test_graph_sync_parser_is_exposed_from_native_module() -> None:
    parser = graph_sync._parser()
    assert "deterministic BioETL graph" in (parser.description or "")


def test_graph_sync_prefers_canonical_mapping_path() -> None:
    mapping_path = graph_sync._memory_mapping_path(graph_sync.DEFAULT_ROOT)
    assert (
        mapping_path == graph_sync.DEFAULT_ROOT / graph_sync.DEFAULT_MEMORY_MAPPING_PATH
    )


def test_graph_ontology_and_mapping_assets_exist() -> None:
    graph_root = Path("src/memory/graph")
    mappings = graph_root / "mappings.yaml"
    ontology = graph_root / "ontology.yaml"

    assert mappings.exists()
    assert ontology.exists()

    ontology_payload = yaml.safe_load(ontology.read_text(encoding="utf-8"))
    assert (
        ontology_payload["canonical_mapping_path"] == "src/memory/graph/mappings.yaml"
    )
    assert "topology" in ontology_payload["node_families"]


def test_memory_graph_main_dispatches_sync(monkeypatch) -> None:
    called: list[list[str]] = []

    def _sync(argv: list[str] | None = None) -> int:
        called.append(argv or [])
        return 0

    monkeypatch.setitem(graph_main.COMMANDS, "sync", _sync)
    assert graph_main.main(["sync", "--help"]) == 0
    assert called == [["--help"]]


def test_memory_graph_main_rejects_unknown_command() -> None:
    assert graph_main.main(["unknown"]) == 2
