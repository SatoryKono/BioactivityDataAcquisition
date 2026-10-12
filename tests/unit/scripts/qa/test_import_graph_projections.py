# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Fixture coverage for the shared import-graph resolver projections."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

import scripts.engineering.qa.import_graph_inventory as import_graph_inventory
from scripts.engineering.qa.import_graph_inventory import (
    FAILURE_OVERSIZE,
    FAILURE_PARSE_ERROR,
    FAILURE_UNREADABLE,
    NON_CONSTANT_IMPORT_TARGET,
    PROJECTION_DYNAMIC_RESOLVED,
    PROJECTION_DYNAMIC_UNRESOLVED,
    PROJECTION_IMPORT_TIME_RUNTIME,
    PROJECTION_LABELS,
    PROJECTION_NAMES,
    PROJECTION_OWNERSHIP,
    PROJECTION_TYPE_ONLY,
    RESOLUTION_RESOLVED,
    RESOLUTION_SYMBOL_NOT_MODULE,
    SYNTAX_DUNDER_IMPORT,
    SYNTAX_IMPORT,
    SYNTAX_IMPORT_FROM,
    SYNTAX_IMPORT_MODULE,
    TIMING_DEFERRED,
    TIMING_MODULE_IMPORT_TIME,
    TIMING_TYPE_CHECKING,
    ImportEdge,
    _MAX_SOURCE_BYTES,
    _PARSED_CACHE_VERSION,
    _read_module_source,
    collect_bioetl_importers,
    collect_import_graph,
    default_scan_roots,
    find_import_cycles,
    find_import_sccs,
    scan_roots,
)
from scripts.engineering.qa.import_graph_inventory import ImportGraphReport


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _resolved(report: ImportGraphReport, source: str) -> set[str]:
    return {
        edge.target
        for edge in report.edges
        if edge.source == source and edge.resolution == RESOLUTION_RESOLVED
    }


def test_deep_cycle_detection_uses_explicit_stacks() -> None:
    """Valid graphs deeper than Python's recursion limit remain analyzable."""
    node_count = 1_500
    chain_edges = tuple(
        ImportEdge(
            source=f"bioetl.deep.n{index}",
            target=f"bioetl.deep.n{index + 1}",
            file=f"src/bioetl/deep/n{index}.py",
            line=1,
            syntax=SYNTAX_IMPORT,
            resolution=RESOLUTION_RESOLVED,
            timing=TIMING_MODULE_IMPORT_TIME,
        )
        for index in range(node_count - 1)
    )
    edges = (
        *chain_edges,
        ImportEdge(
            source=f"bioetl.deep.n{node_count - 1}",
            target="bioetl.deep.n0",
            file=f"src/bioetl/deep/n{node_count - 1}.py",
            line=1,
            syntax=SYNTAX_IMPORT,
            resolution=RESOLUTION_RESOLVED,
            timing=TIMING_MODULE_IMPORT_TIME,
        ),
    )

    components = find_import_sccs(edges)
    cycles = find_import_cycles(edges, projection=PROJECTION_OWNERSHIP)

    assert len(components) == 1
    assert len(components[0]) == node_count
    assert len(cycles) == 1
    assert len(cycles[0].path) == node_count


def test_projection_names_and_cache_version() -> None:
    assert _PARSED_CACHE_VERSION == 4
    assert PROJECTION_NAMES == (
        PROJECTION_IMPORT_TIME_RUNTIME,
        PROJECTION_OWNERSHIP,
        PROJECTION_TYPE_ONLY,
        PROJECTION_DYNAMIC_RESOLVED,
        PROJECTION_DYNAMIC_UNRESOLVED,
    )
    assert PROJECTION_LABELS[PROJECTION_IMPORT_TIME_RUNTIME] == "import-time runtime"
    assert PROJECTION_LABELS[PROJECTION_OWNERSHIP] == "ownership"
    assert PROJECTION_LABELS[PROJECTION_TYPE_ONLY] == "type-only"
    assert PROJECTION_LABELS[PROJECTION_DYNAMIC_RESOLVED] == "dynamic resolved"
    assert PROJECTION_LABELS[PROJECTION_DYNAMIC_UNRESOLVED] == "dynamic unresolved"


def test_relative_import_from_package_init_and_sibling(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")
    _write(
        tmp_path / "src/bioetl/pkg/__init__.py",
        "from .child import VALUE\nfrom . import child\n",
    )
    _write(tmp_path / "src/bioetl/pkg/sibling.py", "from .child import VALUE\n")

    report = collect_import_graph(tmp_path)

    assert report.passed is True
    assert _resolved(report, "bioetl.pkg") == {"bioetl.pkg.child"}
    assert _resolved(report, "bioetl.pkg.sibling") == {"bioetl.pkg.child"}
    assert all(edge.source != edge.target for edge in report.edges)
    assert "bioetl.child" not in {edge.target for edge in report.edges}
    assert "bioetl.pkg.sibling.child" not in {edge.target for edge in report.edges}
    assert all(
        edge.syntax == SYNTAX_IMPORT_FROM and edge.timing == TIMING_MODULE_IMPORT_TIME
        for edge in report.edges
        if edge.resolution == RESOLUTION_RESOLVED
    )


def test_child_module_is_not_confused_with_symbol(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "TOKEN = 1\n")
    _write(
        tmp_path / "src/bioetl/pkg/consumer.py",
        "from bioetl.pkg import child\nfrom bioetl.pkg.child import TOKEN\n",
    )

    report = collect_import_graph(tmp_path)

    assert _resolved(report, "bioetl.pkg.consumer") == {
        "bioetl.pkg",
        "bioetl.pkg.child",
    }
    assert not any(
        edge.resolution == RESOLUTION_RESOLVED
        and edge.target == "bioetl.pkg.child.TOKEN"
        for edge in report.edges
    )
    assert any(
        edge.resolution == RESOLUTION_SYMBOL_NOT_MODULE
        and edge.target == "bioetl.pkg.child.TOKEN"
        for edge in report.edges
    )
    assert all(
        edge.resolution != RESOLUTION_SYMBOL_NOT_MODULE
        for edge in report.projections.import_time_runtime
    )


def test_import_alias_does_not_retarget_later_imports(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/real.py", "VALUE = 1\n")
    _write(tmp_path / "src/bioetl/pkg/decoy.py", "VALUE = 2\n")
    _write(
        tmp_path / "src/bioetl/pkg/consumer.py",
        "import bioetl.pkg.real as decoy\nimport bioetl.pkg.decoy\n",
    )

    report = collect_import_graph(tmp_path)
    targets = _resolved(report, "bioetl.pkg.consumer")

    assert targets == {"bioetl.pkg.real", "bioetl.pkg.decoy"}
    assert "decoy" not in targets
    assert "bioetl.pkg.real.decoy" not in {edge.target for edge in report.edges}


def test_star_and_name_reexports_target_the_child_module(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/child.py", "class PublicName:\n    pass\n")
    _write(
        tmp_path / "src/bioetl/pkg/__init__.py",
        "from .child import PublicName\n__all__ = ['PublicName']\n",
    )
    _write(tmp_path / "src/bioetl/pkg/facade.py", "from bioetl.pkg.child import *\n")

    report = collect_import_graph(tmp_path)
    facade_edges = [edge for edge in report.edges if edge.source == "bioetl.pkg.facade"]

    assert len(facade_edges) == 1
    assert facade_edges[0].target == "bioetl.pkg.child"
    assert facade_edges[0].resolution == RESOLUTION_RESOLVED
    assert facade_edges[0].syntax == SYNTAX_IMPORT_FROM
    assert "bioetl.pkg.child" in _resolved(report, "bioetl.pkg")
    assert any(
        edge.resolution == RESOLUTION_SYMBOL_NOT_MODULE
        and edge.target == "bioetl.pkg.child.PublicName"
        for edge in report.edges
    )


def test_type_checking_alias_and_shadow_use_enclosing_if(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    for name in ("child", "other", "else_child", "shadowed"):
        _write(tmp_path / f"src/bioetl/pkg/{name}.py", "VALUE = 1\n")
    _write(
        tmp_path / "src/bioetl/pkg/consumer.py",
        "\n".join(
            [
                "from typing import TYPE_CHECKING as TC",
                "import typing as t",
                "if TC:",
                "    import bioetl.pkg.child",
                "if t.TYPE_CHECKING:",
                "    from bioetl.pkg.child import VALUE",
                "if not TC:",
                "    import bioetl.pkg.other",
                "else:",
                "    import bioetl.pkg.else_child",
                "TC = 0",
                "if TC:",
                "    import bioetl.pkg.shadowed",
                "",
            ]
        ),
    )

    report = collect_import_graph(tmp_path)

    def timing(target: str) -> set[str]:
        return {
            edge.timing
            for edge in report.edges
            if edge.source == "bioetl.pkg.consumer" and edge.target == target
        }

    assert timing("bioetl.pkg.child") == {TIMING_TYPE_CHECKING}
    assert timing("bioetl.pkg.else_child") == {TIMING_TYPE_CHECKING}
    assert timing("bioetl.pkg.other") == {TIMING_MODULE_IMPORT_TIME}
    assert timing("bioetl.pkg.shadowed") == {TIMING_MODULE_IMPORT_TIME}
    assert "bioetl.pkg.shadowed" not in {
        edge.target for edge in report.projections.type_only
    }
    assert "bioetl.pkg.child" not in {
        edge.target for edge in report.projections.import_time_runtime
    }
    assert any(
        edge.target == "bioetl.pkg.other"
        for edge in report.projections.import_time_runtime
    )


def test_function_and_class_imports_are_deferred(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")
    _write(tmp_path / "src/bioetl/pkg/other.py", "VALUE = 2\n")
    _write(
        tmp_path / "src/bioetl/pkg/consumer.py",
        "\n".join(
            [
                "class Holder:",
                "    import bioetl.pkg.child",
                "def load() -> None:",
                "    import bioetl.pkg.other",
                "",
            ]
        ),
    )

    report = collect_import_graph(tmp_path)
    timings = {(edge.target, edge.timing) for edge in report.edges}

    assert timings == {
        ("bioetl.pkg.child", TIMING_DEFERRED),
        ("bioetl.pkg.other", TIMING_DEFERRED),
    }
    assert report.projections.import_time_runtime == ()
    assert {edge.target for edge in report.projections.ownership} == {
        "bioetl.pkg.child",
        "bioetl.pkg.other",
    }


def test_literal_dynamic_import_resolves_and_computed_is_unresolved(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")
    _write(tmp_path / "src/bioetl/pkg/other.py", "VALUE = 2\n")
    _write(
        tmp_path / "src/bioetl/pkg/consumer.py",
        "\n".join(
            [
                "import importlib",
                "from importlib import import_module as load_module",
                "importlib.import_module('bioetl.pkg.child')",
                "load_module('bioetl.pkg.child')",
                "importlib.import_module('bioetl.pkg.' + 'child')",
                "__import__('bioetl.pkg.child')",
                "__import__('bioetl.' + 'missing')",
                "def later() -> None:",
                "    importlib.import_module('bioetl.pkg.other')",
                "",
            ]
        ),
    )

    report = collect_import_graph(tmp_path)

    assert report.passed is True
    resolved = {
        (edge.syntax, edge.timing, edge.target)
        for edge in report.projections.dynamic_resolved
    }
    assert resolved == {
        (SYNTAX_IMPORT_MODULE, TIMING_MODULE_IMPORT_TIME, "bioetl.pkg.child"),
        (SYNTAX_DUNDER_IMPORT, TIMING_MODULE_IMPORT_TIME, "bioetl.pkg.child"),
        (SYNTAX_IMPORT_MODULE, TIMING_DEFERRED, "bioetl.pkg.other"),
    }
    assert (
        sum(
            1
            for edge in report.projections.dynamic_resolved
            if edge.syntax == SYNTAX_IMPORT_MODULE
            and edge.timing == TIMING_MODULE_IMPORT_TIME
        )
        == 2
    )
    assert {
        (edge.syntax, edge.target) for edge in report.projections.dynamic_unresolved
    } == {
        (SYNTAX_IMPORT_MODULE, NON_CONSTANT_IMPORT_TARGET),
        (SYNTAX_DUNDER_IMPORT, NON_CONSTANT_IMPORT_TARGET),
    }
    assert report.projections.import_time_runtime == ()
    assert len(report.projections.ownership) == 4


def test_parse_error_fails_the_report_and_survives_the_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIOETL_IMPORT_GRAPH_CACHE_DIR", str(tmp_path / "cache"))
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")
    _write(tmp_path / "src/bioetl/pkg/ok.py", "import bioetl.pkg.child\n")
    _write(tmp_path / "src/bioetl/pkg/bad.py", "def (\n")

    report = collect_import_graph(tmp_path)

    assert report.passed is False
    assert any(
        failure.reason == FAILURE_PARSE_ERROR
        and failure.file == "src/bioetl/pkg/bad.py"
        for failure in report.failures
    )
    assert any(
        edge.file == "src/bioetl/pkg/ok.py" and edge.target == "bioetl.pkg.child"
        for edge in report.edges
    )
    import_graph_inventory._collect_import_scan.cache_clear()
    again = collect_import_graph(tmp_path)
    assert again.passed is False
    assert again.failures == report.failures


def test_oversize_source_is_reported_and_not_parsed(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "VALUE = 1\n")
    _write(
        tmp_path / "src/bioetl/pkg/huge.py",
        "import bioetl.pkg.child\nVALUE = '" + ("A" * (_MAX_SOURCE_BYTES + 8)) + "'\n",
    )

    report = collect_import_graph(tmp_path)

    assert report.passed is False
    assert any(
        failure.reason == FAILURE_OVERSIZE and failure.file == "src/bioetl/pkg/huge.py"
        for failure in report.failures
    )
    assert not any(edge.file == "src/bioetl/pkg/huge.py" for edge in report.edges)


def test_read_module_source_reports_missing_file(tmp_path: Path) -> None:
    read = _read_module_source(("bioetl.missing", tmp_path / "missing.py"))

    assert read.text is None
    assert read.failure_reason == FAILURE_UNREADABLE


def test_unreadable_source_fails_the_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/locked.py", "import bioetl.pkg\n")
    real_read = import_graph_inventory._read_module_source

    def wrapped(item: tuple[str, Path]) -> object:
        module_name, path = item
        if path.name == "locked.py":
            return import_graph_inventory._SourceRead(
                module_name,
                path,
                None,
                FAILURE_UNREADABLE,
                "OSError",
            )
        return real_read(item)

    monkeypatch.setattr(import_graph_inventory, "_read_module_source", wrapped)
    report = collect_import_graph(tmp_path)

    assert report.passed is False
    assert any(
        failure.reason == FAILURE_UNREADABLE
        and failure.file == "src/bioetl/pkg/locked.py"
        for failure in report.failures
    )


def test_pyi_imports_are_type_only_and_still_census_importers(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/child.py", "class Port:\n    pass\n")
    _write(tmp_path / "src/bioetl/pkg/api.pyi", "from bioetl.pkg.child import Port\n")

    report = collect_import_graph(tmp_path)
    pyi_edges = [edge for edge in report.edges if edge.file == "src/bioetl/pkg/api.pyi"]

    assert pyi_edges
    assert all(edge.timing == TIMING_TYPE_CHECKING for edge in pyi_edges)
    assert any(edge.resolution == RESOLUTION_RESOLVED for edge in pyi_edges)
    assert not any(
        edge.file.endswith(".pyi") for edge in report.projections.import_time_runtime
    )
    assert not any(edge.file.endswith(".pyi") for edge in report.projections.ownership)
    assert any(edge.file.endswith(".pyi") for edge in report.projections.type_only)
    importers = collect_bioetl_importers(tmp_path)
    assert importers["bioetl.pkg.child"]["src"] == ("src/bioetl/pkg/api.pyi",)


def test_memory_package_is_included_only_on_the_wide_root(tmp_path: Path) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/bridge.py", "import memory.notes\n")
    _write(tmp_path / "src/memory/__init__.py", "")
    _write(tmp_path / "src/memory/notes.py", "import memory.other\n")
    _write(tmp_path / "src/memory/other.py", "VALUE = 1\n")

    assert [scan.module_prefix for scan in default_scan_roots(tmp_path)] == [
        "bioetl",
        "tests",
    ]
    wide = scan_roots(tmp_path, include_memory=True)
    assert [scan.module_prefix for scan in wide] == ["bioetl", "tests", "memory"]
    assert wide[-1].label == "memory"

    narrow = collect_import_graph(tmp_path)
    assert all(not edge.source.startswith("memory.") for edge in narrow.edges)
    assert all(not edge.target.startswith("memory.") for edge in narrow.edges)

    by_flag = collect_import_graph(tmp_path, include_memory=True)
    by_roots = collect_import_graph(tmp_path, roots=wide)
    assert by_flag.edges == by_roots.edges
    assert any(
        edge.source == "memory.notes" and edge.target == "memory.other"
        for edge in by_flag.projections.import_time_runtime
    )
    assert any(
        edge.source == "bioetl.pkg.bridge" and edge.target == "memory.notes"
        for edge in by_flag.projections.import_time_runtime
    )
    resolver = Path(import_graph_inventory.__file__).read_text(encoding="utf-8")
    assert "LAYER_IMPORT_MATRIX" not in resolver


def test_deferred_edge_closes_ownership_cycle_not_import_time_cycle(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "src/bioetl/pkg/__init__.py", "")
    _write(tmp_path / "src/bioetl/pkg/left.py", "import bioetl.pkg.right\n")
    _write(
        tmp_path / "src/bioetl/pkg/right.py",
        "def close() -> None:\n    import bioetl.pkg.left\n",
    )

    report = collect_import_graph(tmp_path)
    import_pairs = {
        (edge.source, edge.target) for edge in report.projections.import_time_runtime
    }
    ownership_pairs = {
        (edge.source, edge.target) for edge in report.projections.ownership
    }

    assert import_pairs == {("bioetl.pkg.left", "bioetl.pkg.right")}
    assert ownership_pairs == {
        ("bioetl.pkg.left", "bioetl.pkg.right"),
        ("bioetl.pkg.right", "bioetl.pkg.left"),
    }
    assert (
        find_import_cycles(
            report.projections.import_time_runtime,
            projection=PROJECTION_IMPORT_TIME_RUNTIME,
        )
        == ()
    )
    cycles = find_import_cycles(
        report.projections.ownership,
        projection=PROJECTION_OWNERSHIP,
    )
    assert cycles == find_import_cycles(
        tuple(reversed(report.projections.ownership)),
        projection=PROJECTION_OWNERSHIP,
    )
    assert len(cycles) == 1
    cycle = cycles[0]
    assert cycle.projection == PROJECTION_OWNERSHIP
    assert cycle.path == ("bioetl.pkg.left", "bioetl.pkg.right")
    assert len(cycle.edges) == len(cycle.path)
    assert cycle.edges[0].timing == TIMING_MODULE_IMPORT_TIME
    assert cycle.edges[0].file == "src/bioetl/pkg/left.py"
    assert cycle.edges[0].line == 1
    assert cycle.edges[0].syntax == SYNTAX_IMPORT
    assert cycle.edges[1].timing == TIMING_DEFERRED
    assert cycle.edges[1].file == "src/bioetl/pkg/right.py"
    assert cycle.edges[1].line == 2
    assert cycle.edges[1].syntax == SYNTAX_IMPORT
