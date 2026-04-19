"""Guardrails for application.composite compatibility surfaces."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMPAT_PARENT_IMPORTS: dict[str, frozenset[str]] = {}
ALLOWED_SRC_IMPORTS: dict[str, frozenset[Path]] = {}
ALLOWED_TEST_IMPORTS: dict[str, frozenset[Path]] = {}
REMOVED_COMPAT_MODULES = frozenset(
    {
        "bioetl.application.composite.merger_compat_mixin",
        "bioetl.application.composite.merger_compat_join_planner_mixin",
        "bioetl.application.composite.join_planner_compat_mixin",
        "bioetl.application.composite.runner",
    }
)
REMOVED_COMPAT_PARENT_IMPORTS = {
    "bioetl.application.composite": frozenset(
        {
            "merger_compat_mixin",
            "join_planner_compat_mixin",
            "runner",
        }
    )
}
REMOVED_COMPAT_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "composite"
        / "merger_compat_mixin.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "composite"
        / "merger_compat_join_planner_mixin.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "composite"
        / "join_planner_compat_mixin.py",
        ROOT / "src" / "bioetl" / "application" / "composite" / "runner.py",
    }
)


def _iter_import_records(
    ast_cache: dict[Path, ast.Module],
) -> list[tuple[Path, int, str]]:
    records: list[tuple[Path, int, str]] = []
    for py_file, tree in sorted(ast_cache.items()):
        for node in ast.walk(tree):
            records.extend(_iter_node_import_records(py_file, node))
    return records


def _format_violations(
    records: list[tuple[Path, int, str]],
    *,
    allowed_imports: dict[str, frozenset[Path]],
) -> list[str]:
    violations: list[str] = []
    for py_file, lineno, module_name in records:
        if py_file in allowed_imports[module_name]:
            continue
        rel_path = py_file.relative_to(ROOT).as_posix()
        violations.append(f"{rel_path}:{lineno} imports {module_name}")
    return violations


def _iter_removed_import_records(
    ast_cache: dict[Path, ast.Module],
) -> list[tuple[Path, int, str]]:
    records: list[tuple[Path, int, str]] = []
    for py_file, tree in sorted(ast_cache.items()):
        for node in ast.walk(tree):
            records.extend(_iter_removed_node_import_records(py_file, node))
    return records


def _iter_node_import_records(
    py_file: Path,
    node: ast.AST,
) -> list[tuple[Path, int, str]]:
    if isinstance(node, ast.ImportFrom):
        return _iter_import_from_records(
            py_file,
            node,
            direct_modules=ALLOWED_SRC_IMPORTS,
            parent_imports=COMPAT_PARENT_IMPORTS,
        )
    if isinstance(node, ast.Import):
        return [
            (py_file, node.lineno, alias.name)
            for alias in node.names
            if alias.name in ALLOWED_SRC_IMPORTS
        ]
    return []


def _iter_removed_node_import_records(
    py_file: Path,
    node: ast.AST,
) -> list[tuple[Path, int, str]]:
    if isinstance(node, ast.ImportFrom):
        return _iter_import_from_records(
            py_file,
            node,
            direct_modules=REMOVED_COMPAT_MODULES,
            parent_imports=REMOVED_COMPAT_PARENT_IMPORTS,
        )
    if isinstance(node, ast.Import):
        return [
            (py_file, node.lineno, alias.name)
            for alias in node.names
            if alias.name in REMOVED_COMPAT_MODULES
        ]
    return []


def _iter_import_from_records(
    py_file: Path,
    node: ast.ImportFrom,
    *,
    direct_modules: set[str] | frozenset[str] | dict[str, frozenset[Path]],
    parent_imports: dict[str, frozenset[str]],
) -> list[tuple[Path, int, str]]:
    if node.module in direct_modules:
        return [(py_file, node.lineno, node.module)]
    if node.module not in parent_imports:
        return []
    compat_children = parent_imports[node.module]
    return [
        (py_file, node.lineno, f"{node.module}.{alias.name}")
        for alias in node.names
        if alias.name in compat_children
    ]


@pytest.mark.architecture
def test_application_composite_compat_surfaces_are_confined_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must not grow new imports of active composite compat modules."""
    violations = _format_violations(
        _iter_import_records(source_ast_cache),
        allowed_imports=ALLOWED_SRC_IMPORTS,
    )
    assert not violations, (
        "application.composite compatibility surfaces leaked beyond allowed src files:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_application_composite_compat_surfaces_are_confined_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Ordinary tests must not accumulate new imports of active composite compat modules."""
    violations = _format_violations(
        _iter_import_records(test_ast_cache),
        allowed_imports=ALLOWED_TEST_IMPORTS,
    )
    assert not violations, (
        "application.composite compatibility surfaces gained new non-smoke test imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_removed_application_composite_compat_shim_files_stay_absent() -> None:
    """Removed application.composite compat shims should stay absent."""
    lingering = sorted(
        path.relative_to(ROOT).as_posix()
        for path in REMOVED_COMPAT_FILES
        if path.exists()
    )
    assert not lingering, (
        "Removed application.composite compat shims must stay absent:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_removed_application_composite_compat_shims_are_not_imported(
    source_ast_cache: dict[Path, ast.Module],
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Removed application.composite compat shims must not be imported."""
    records = _iter_removed_import_records(source_ast_cache)
    records.extend(_iter_removed_import_records(test_ast_cache))
    violations = [
        f"{py_file.relative_to(ROOT).as_posix()}:{lineno} imports {module_name}"
        for py_file, lineno, module_name in records
    ]
    assert not violations, (
        "Removed application.composite compat shims must stay absent from imports:\n"
        + "\n".join(violations)
    )
