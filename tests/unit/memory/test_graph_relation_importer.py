"""Tests for expanded graph relation import projections."""

from __future__ import annotations

import json
from pathlib import Path

from memory.graph.importers.expanded_json import (
    load_file_relation_index,
    load_module_relation_index,
    query_file_neighborhood,
    query_file_relations,
    query_module_neighborhood,
    query_module_relations,
    write_expanded_graph_relation_artifacts,
)


def _write_expanded_graph(path: Path) -> None:
    payload = {
        "meta": {"generated_at": "2026-04-17", "node_count": 3, "edge_count": 2},
        "nodes": {
            "file:src/a.py": {
                "id": "file:src/a.py",
                "node_type": "File",
                "source_path": "src/a.py",
                "label": "a.py",
            },
            "file:src/b.py": {
                "id": "file:src/b.py",
                "node_type": "File",
                "source_path": "src/b.py",
                "label": "b.py",
            },
            "file:src/c.py": {
                "id": "file:src/c.py",
                "node_type": "File",
                "source_path": "src/c.py",
                "label": "c.py",
            },
            "mod:pkg.a": {
                "id": "mod:pkg.a",
                "node_type": "Module",
                "source_path": "src/a.py",
                "label": "pkg.a",
            },
            "mod:pkg.b": {
                "id": "mod:pkg.b",
                "node_type": "Module",
                "source_path": "src/b.py",
                "label": "pkg.b",
            },
            "mod:pkg.c": {
                "id": "mod:pkg.c",
                "node_type": "Module",
                "source_path": "src/c.py",
                "label": "pkg.c",
            },
        },
        "edges": {
            "src/a.py|references_file|src/b.py": {
                "source": "file:src/a.py",
                "target": "file:src/b.py",
                "edge_type": "references_file",
                "meta": {"statement_count": 2},
            },
            "src/b.py|references_file|src/c.py": {
                "source": "file:src/b.py",
                "target": "file:src/c.py",
                "edge_type": "references_file",
                "meta": {"statement_count": 1},
            },
            "pkg.a|references|pkg.b": {
                "source": "mod:pkg.a",
                "target": "mod:pkg.b",
                "edge_type": "references",
                "meta": {"statement_count": 2},
            },
            "pkg.b|references|pkg.c": {
                "source": "mod:pkg.b",
                "target": "mod:pkg.c",
                "edge_type": "references",
                "meta": {"statement_count": 1},
            },
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_expanded_graph_import_writes_file_relation_projection_and_index(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "bioetl_knowledge_graph_expanded.json"
    _write_expanded_graph(snapshot_path)

    projection_path, index_path, summary = write_expanded_graph_relation_artifacts(
        snapshot_path,
        tmp_path / "memory",
    )

    assert summary["relation_count"] == 2
    assert summary["module_relation_count"] == 2
    assert projection_path.exists()
    assert index_path.exists()
    assert Path(summary["module_projection_path"]).exists()
    assert Path(summary["module_index_path"]).exists()
    assert len(projection_path.read_text(encoding="utf-8").splitlines()) == 2


def test_file_relation_index_queries_direct_refs_and_neighborhood(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "bioetl_knowledge_graph_expanded.json"
    _write_expanded_graph(snapshot_path)
    _, index_path, _ = write_expanded_graph_relation_artifacts(
        snapshot_path,
        tmp_path / "memory",
    )
    index = load_file_relation_index(index_path)

    refs = query_file_relations(index, "a.py", direction="outbound")
    neighborhood = query_file_neighborhood(index, "src/a.py", depth=2)

    assert refs["resolved_path"] == "src/a.py"
    assert refs["outbound"][0]["target_path"] == "src/b.py"
    assert neighborhood["nodes"] == ["src/a.py", "src/b.py", "src/c.py"]
    assert len(neighborhood["edges"]) == 2


def test_module_relation_index_queries_direct_refs_and_neighborhood(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "bioetl_knowledge_graph_expanded.json"
    _write_expanded_graph(snapshot_path)
    _, _, summary = write_expanded_graph_relation_artifacts(
        snapshot_path,
        tmp_path / "memory",
    )
    index = load_module_relation_index(Path(summary["module_index_path"]))

    refs = query_module_relations(index, "a", direction="outbound")
    neighborhood = query_module_neighborhood(index, "pkg.a", depth=2)

    assert refs["resolved_module"] == "pkg.a"
    assert refs["outbound"][0]["target_name"] == "pkg.b"
    assert neighborhood["nodes"] == ["pkg.a", "pkg.b", "pkg.c"]
    assert len(neighborhood["edges"]) == 2
