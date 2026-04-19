"""Guardrails for removed pipeline/storage compatibility-only facade imports."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REMOVED_PIPELINE_STORAGE_COMPAT_MODULES = frozenset(
    {
        "bioetl.composition.factories.pipeline.facade",
        "bioetl.composition.factories.storage.facade",
        "bioetl.infrastructure.storage.delta_writer",
        "bioetl.infrastructure.storage.silver_writer_runtime_helpers",
    }
)
REMOVED_PIPELINE_STORAGE_PARENT_IMPORTS = {
    "bioetl.composition.factories.pipeline": frozenset({"facade"}),
    "bioetl.composition.factories.storage": frozenset({"facade"}),
    "bioetl.infrastructure.storage": frozenset(
        {"delta_writer", "silver_writer_runtime_helpers"}
    ),
}
REMOVED_PIPELINE_STORAGE_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "pipeline"
        / "facade.py",
        ROOT / "src" / "bioetl" / "composition" / "factories" / "storage" / "facade.py",
        ROOT / "src" / "bioetl" / "infrastructure" / "storage" / "delta_writer.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "storage"
        / "silver_writer_runtime_helpers.py",
    }
)


def _iter_removed_compat_import_violations(
    ast_cache: dict[Path, ast.Module],
) -> list[str]:
    violations: list[str] = []
    for py_file, tree in sorted(ast_cache.items()):
        rel_path = py_file.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            violations.extend(
                f"{rel_path}:{node.lineno} imports {compat_path}"
                for compat_path in _iter_node_compat_paths(node)
            )
    return violations


def _iter_node_compat_paths(node: ast.AST) -> list[str]:
    if isinstance(node, ast.ImportFrom):
        return _iter_import_from_compat_paths(node)
    if isinstance(node, ast.Import):
        return [
            alias.name
            for alias in node.names
            if alias.name in REMOVED_PIPELINE_STORAGE_COMPAT_MODULES
        ]
    return []


def _iter_import_from_compat_paths(node: ast.ImportFrom) -> list[str]:
    if node.module in REMOVED_PIPELINE_STORAGE_COMPAT_MODULES:
        return [node.module]
    if node.module not in REMOVED_PIPELINE_STORAGE_PARENT_IMPORTS:
        return []
    compat_children = REMOVED_PIPELINE_STORAGE_PARENT_IMPORTS[node.module]
    return [
        f"{node.module}.{alias.name}"
        for alias in node.names
        if alias.name in compat_children
    ]


@pytest.mark.architecture
def test_removed_pipeline_storage_compat_files_have_been_removed() -> None:
    """Removed pipeline/storage compatibility shims should no longer exist."""
    lingering = sorted(
        path.relative_to(ROOT).as_posix()
        for path in REMOVED_PIPELINE_STORAGE_FILES
        if path.exists()
    )
    assert not lingering, (
        "Removed pipeline/storage compatibility wrappers must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_removed_pipeline_storage_compat_shims_are_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party source code must use canonical pipeline/storage modules directly."""
    violations = _iter_removed_compat_import_violations(source_ast_cache)
    assert not violations, (
        "Removed pipeline/storage compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_removed_pipeline_storage_compat_shims_are_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing removed pipeline/storage compatibility modules."""
    violations = _iter_removed_compat_import_violations(test_ast_cache)
    assert not violations, (
        "Removed pipeline/storage compatibility shims must stay absent from tests:\n"
        + "\n".join(violations)
    )
