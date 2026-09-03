"""Tests for canonical ``memory.graph`` entrypoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from memory.graph import __main__ as graph_main
from memory.graph import query as graph_query
from memory.graph import sync as graph_sync
from memory.graph.sync_pkg import apply as graph_sync_apply
from memory.graph.sync_pkg import snapshot as graph_sync_snapshot
from memory.graph.sync_pkg import transport as graph_sync_transport


pytestmark = pytest.mark.unit


def _sync_symbol(name: str) -> Any:
    """Resolve one intentionally dynamic compatibility-facade export."""
    return getattr(graph_sync, name)


def test_graph_sync_facade_exposes_legacy_symbols() -> None:
    assert _sync_symbol("DEFAULT_INGEST_WAVE") == "repo_sync_v1"
    assert callable(_sync_symbol("build_snapshot"))


def test_graph_query_facade_exposes_legacy_symbols() -> None:
    assert "owner-pipeline" in graph_query.QUERY_PROFILES
    assert callable(graph_query.main)


def test_graph_sync_uses_repo_root_from_src_layout() -> None:
    assert (_sync_symbol("DEFAULT_ROOT") / "src" / "bioetl").exists()


def test_graph_query_uses_native_sync_module() -> None:
    assert graph_query.resolve_neo4j_connection is _sync_symbol(
        "resolve_neo4j_connection"
    )


def test_graph_sync_parser_is_exposed_from_native_module() -> None:
    parser = _sync_symbol("_parser")()
    assert "deterministic BioETL graph" in (parser.description or "")


def test_graph_sync_public_module_is_thin_facade() -> None:
    sync_path = Path(graph_sync.__file__ or "")
    assert sync_path.name == "sync.py"
    assert len(sync_path.read_text(encoding="utf-8").splitlines()) <= 25


def test_graph_sync_responsibility_modules_expose_owned_surfaces() -> None:
    assert graph_sync_transport.Neo4jHttpClient is _sync_symbol("Neo4jHttpClient")
    assert graph_sync_snapshot.build_snapshot is _sync_symbol("build_snapshot")
    assert graph_sync_snapshot._walk_repo_zone_file_structure is (
        _sync_symbol("_walk_repo_zone_file_structure")
    )
    assert graph_sync_apply.sync_snapshot is _sync_symbol("sync_snapshot")


def test_graph_sync_prefers_canonical_mapping_path() -> None:
    default_root = _sync_symbol("DEFAULT_ROOT")
    mapping_path = _sync_symbol("_memory_mapping_path")(default_root)
    assert mapping_path == default_root / _sync_symbol("DEFAULT_MEMORY_MAPPING_PATH")


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

def test_analysis_node_batch_size_keeps_complexity_serial_without_collapsing_others() -> None:
    """complexity_candidate stays batch=1; other analysis labels keep their own cap."""
    from memory.graph.sync_pkg._core import _analysis_node_batch_size

    only_complexity = {"complexity_candidate": [{"statement": "x"}]}
    assert _analysis_node_batch_size(only_complexity, 20) == 1

    mixed = {
        "complexity_candidate": [{"statement": "x"}],
        "retirement_candidate": [{"statement": "y"}],
    }
    # retirement_candidate is high-priority, cap 5 — not forced to 1 by complexity.
    assert _analysis_node_batch_size(mixed, 20) == 5

    other = {"other_analysis": [{"statement": "z"}]}
    assert _analysis_node_batch_size(other, 20) == 10

