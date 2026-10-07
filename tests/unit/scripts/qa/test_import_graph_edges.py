"""Import-graph projections, failures, and cycle provenance."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.engineering.qa.import_graph_inventory as import_graph
from scripts.engineering.qa.import_graph_inventory import (
    ImportEdge,
    collect_import_graph,
    default_scan_roots,
    find_import_cycles,
    scan_roots,
)

pytestmark = pytest.mark.unit


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _targets(edges: tuple[ImportEdge, ...], source: str) -> set[tuple[str, str]]:
    return {(edge.target, edge.resolution) for edge in edges if edge.source == source}


def test_default_scan_roots_stay_on_bioetl_and_tests(tmp_path: Path) -> None:
    assert tuple(scan.label for scan in default_scan_roots(tmp_path)) == (
        "src",
        "tests",
    )
    assert tuple(scan.label for scan in scan_roots(tmp_path, include_memory=True)) == (
        "src",
        "tests",
        "memory",
    )


def test_relative_import_from_package_init_resolves_child(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "from .child import Widget\n")
    _write(tmp_path / "src/bioetl/pkg/child.py", "class Widget:\n    pass\n")

    graph = collect_import_graph(tmp_path)

    assert graph.passed
    assert ("bioetl.pkg.child", "resolved") in _targets(graph.edges, "bioetl.pkg")
    assert ("bioetl.pkg.child.Widget", "symbol_not_module") in _targets(
        graph.edges, "bioetl.pkg"
    )


def test_relative_sibling_import_targets_the_child_not_the_parent(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "from .child import VALUE\n")
    _write(tmp_path / "src/bioetl/pkg/child.py", "from . import sibling\nVALUE = 1\n")
    _write(tmp_path / "src/bioetl/pkg/sibling.py", "VALUE = 1\n")
    _write(tmp_path / "src/bioetl/pkg/reader.py", "from . import TOKEN\n")

    graph = collect_import_graph(tmp_path)

    assert _targets(graph.edges, "bioetl.pkg.child") == {
        ("bioetl.pkg.sibling", "resolved"),
    }
    assert ("bioetl.pkg", "resolved") in _targets(graph.edges, "bioetl.pkg.reader")
    assert ("bioetl.pkg.TOKEN", "symbol_not_module") in _targets(
        graph.edges, "bioetl.pkg.reader"
    )
    assert (
        find_import_cycles(
            graph.projections.import_time_runtime,
            projection="import_time_runtime",
        )
        == ()
    )


def test_package_child_is_a_module_and_plain_symbol_is_not(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")
    _write(
        tmp_path / "src/bioetl/pkg/user.py",
        "from bioetl.pkg import child, Widget\n",
    )

    graph = collect_import_graph(tmp_path)

    assert _targets(graph.edges, "bioetl.pkg.user") == {
        ("bioetl.pkg", "resolved"),
        ("bioetl.pkg.child", "resolved"),
        ("bioetl.pkg.Widget", "symbol_not_module"),
    }


def test_import_alias_does_not_become_the_target(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")
    _write(
        tmp_path / "src/bioetl/pkg/user.py",
        "import bioetl.pkg.child as decoy\n",
    )

    graph = collect_import_graph(tmp_path)

    assert _targets(graph.edges, "bioetl.pkg.user") == {
        ("bioetl.pkg.child", "resolved"),
    }


def test_star_reexport_edges_the_module_not_unknown_symbols(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "from bioetl.pkg.child import *\n")
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")

    graph = collect_import_graph(tmp_path)
    recorded = _targets(graph.edges, "bioetl.pkg")

    assert ("bioetl.pkg.child", "resolved") in recorded
    assert all(resolution != "symbol_not_module" for _target, resolution in recorded)


def test_type_checking_alias_is_type_only(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")
    _write(
        tmp_path / "src/bioetl/pkg/user.py",
        "from typing import TYPE_CHECKING as TC\n"
        "if TC:\n"
        "    import bioetl.pkg.child\n"
        "if True:\n"
        "    import bioetl.pkg.child\n",
    )

    projections = collect_import_graph(tmp_path).projections
    type_lines = {
        edge.line for edge in projections.type_only if edge.source == "bioetl.pkg.user"
    }
    runtime_lines = {
        edge.line
        for edge in projections.import_time_runtime
        if edge.source == "bioetl.pkg.user"
    }

    assert type_lines == {3}
    assert runtime_lines == {5}


def test_deferred_edge_closes_ownership_cycle_only(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/a.py", "import bioetl.pkg.b\n")
    _write(
        tmp_path / "src/bioetl/pkg/b.py",
        "def load() -> None:\n    import bioetl.pkg.a\n",
    )

    projections = collect_import_graph(tmp_path).projections
    runtime_cycles = find_import_cycles(
        projections.import_time_runtime,
        projection="import_time_runtime",
    )
    ownership_cycles = find_import_cycles(
        projections.ownership,
        projection="ownership",
    )

    assert runtime_cycles == ()
    assert len(ownership_cycles) == 1
    assert set(ownership_cycles[0].path) == {"bioetl.pkg.a", "bioetl.pkg.b"}
    deferred = [edge for edge in ownership_cycles[0].edges if edge.timing == "deferred"]
    assert len(deferred) == 1
    assert deferred[0].file == "src/bioetl/pkg/b.py"
    assert deferred[0].line == 2


def test_literal_dynamic_import_resolves_and_computed_stays_unresolved(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")
    _write(
        tmp_path / "src/bioetl/pkg/loader.py",
        "import importlib\n"
        "from importlib import import_module\n"
        'importlib.import_module("bioetl.pkg.child")\n'
        'import_module("bioetl.pkg.absent")\n'
        'importlib.import_module("bioetl.pkg." + "child")\n'
        '__import__("bioetl.pkg.child")\n',
    )

    projections = collect_import_graph(tmp_path).projections
    resolved = {(edge.syntax, edge.target) for edge in projections.dynamic_resolved}
    unresolved = {(edge.syntax, edge.target) for edge in projections.dynamic_unresolved}

    assert ("import_module", "bioetl.pkg.child") in resolved
    assert ("dunder_import", "bioetl.pkg.child") in resolved
    assert ("import_module", "bioetl.pkg.absent") in unresolved
    assert ("import_module", "<non-constant>") in unresolved


def test_parse_error_fails_the_report(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/broken.py", "def broken(\n")

    graph = collect_import_graph(tmp_path)

    assert not graph.passed
    assert any(
        failure.reason == "parse_error" and failure.file.endswith("broken.py")
        for failure in graph.failures
    )


def test_oversize_source_fails_the_report(tmp_path: Path, monkeypatch) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/wide.py", "VALUE = 'abcdefghij'\n")
    monkeypatch.setattr(import_graph, "_MAX_SOURCE_BYTES", 8)
    import_graph._collect_import_scan.cache_clear()

    graph = collect_import_graph(tmp_path)

    assert not graph.passed
    assert any(failure.reason == "oversize" for failure in graph.failures)


def test_unreadable_source_is_a_failure(tmp_path: Path) -> None:
    read = import_graph._read_module_source(("missing", tmp_path / "missing.py"))

    assert read.text is None
    assert read.failure_reason == "unreadable"


def test_stub_import_stays_on_the_type_only_projection(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")
    _write(tmp_path / "src/bioetl/pkg/extra.pyi", "import bioetl.pkg.child\n")

    projections = collect_import_graph(tmp_path).projections

    assert any(
        edge.file.endswith(".pyi") and edge.target == "bioetl.pkg.child"
        for edge in projections.type_only
    )
    assert all(
        not edge.file.endswith(".pyi") for edge in projections.import_time_runtime
    )


def test_memory_root_is_visible_only_on_the_wide_scan(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/__init__.py", "")
    _write(tmp_path / "src/memory/__init__.py", "")
    _write(tmp_path / "src/memory/other.py", "VALUE = 1\n")
    _write(tmp_path / "src/memory/note.py", "import memory.other\n")

    default_graph = collect_import_graph(tmp_path)
    wide_graph = collect_import_graph(tmp_path, include_memory=True)

    assert all(edge.source != "memory.note" for edge in default_graph.edges)
    assert any(
        edge.source == "memory.note"
        and edge.target == "memory.other"
        and edge.resolution == "resolved"
        for edge in wide_graph.edges
    )
