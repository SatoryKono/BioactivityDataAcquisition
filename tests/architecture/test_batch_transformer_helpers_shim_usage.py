"""Guardrails for batch_transformer_helpers compatibility shim."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMPAT_MODULE = "bioetl.application.core.batch_transformer_helpers"
REMOVED_FILE = (
    ROOT / "src" / "bioetl" / "application" / "core" / "batch_transformer_helpers.py"
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.application.core": frozenset({"batch_transformer_helpers"}),
}


def _iter_compat_import_violations(
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
        return [alias.name for alias in node.names if alias.name == COMPAT_MODULE]
    return []


def _iter_import_from_compat_paths(node: ast.ImportFrom) -> list[str]:
    if node.module == COMPAT_MODULE:
        return [COMPAT_MODULE]
    if node.module not in COMPAT_PARENT_IMPORTS:
        return []
    compat_children = COMPAT_PARENT_IMPORTS[node.module]
    return [
        f"{node.module}.{alias.name}"
        for alias in node.names
        if alias.name in compat_children
    ]


@pytest.mark.architecture
def test_batch_transformer_helpers_shim_file_has_been_removed() -> None:
    """The batch_transformer_helpers compatibility module should no longer exist."""
    assert not REMOVED_FILE.exists(), (
        "batch_transformer_helpers compatibility shim must stay removed: "
        "src/bioetl/application/core/batch_transformer_helpers.py"
    )


@pytest.mark.architecture
def test_batch_transformer_helpers_shim_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import canonical batch-transform helper modules directly."""
    violations = _iter_compat_import_violations(source_ast_cache)
    assert not violations, (
        "batch_transformer_helpers compatibility shim is still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_batch_transformer_helpers_shim_is_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing the removed helper shim."""
    violations = _iter_compat_import_violations(test_ast_cache)
    assert not violations, (
        "batch_transformer_helpers compatibility shim must stay removed from tests:\n"
        + "\n".join(violations)
    )
