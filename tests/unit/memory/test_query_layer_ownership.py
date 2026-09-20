"""Lock AUD-003: query layers keep split ownership, no duplicated symbols."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
GRAPH_QUERY = ROOT / "src" / "memory" / "graph" / "query.py"
TOP_QUERY = ROOT / "src" / "memory" / "query.py"


def _public_symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (
                [node.target]
                if isinstance(node, ast.AnnAssign)
                else list(node.targets)
            )
            for target in targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    names.add(target.id)
    return names


def test_query_layers_share_no_public_symbols() -> None:
    overlap = _public_symbols(GRAPH_QUERY) & _public_symbols(TOP_QUERY)
    assert overlap == set()


def test_query_layers_document_split_ownership() -> None:
    for path in (GRAPH_QUERY, TOP_QUERY):
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
        assert doc is not None and "Ownership:" in doc, path.name


def test_graph_cli_entry_has_distinct_name() -> None:
    import memory.graph.query as graph_query

    assert callable(graph_query.graph_query_main)
    assert not hasattr(graph_query, "main")


def test_top_query_facade_passes_graph_through() -> None:
    import memory.graph.query as graph_query
    import memory.query as top_query

    assert top_query.graph_query is graph_query
    assert callable(top_query.main)
