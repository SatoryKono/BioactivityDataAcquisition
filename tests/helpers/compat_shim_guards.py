"""Shared helpers for architecture tests guarding removed compatibility shims."""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from pathlib import Path


def find_lingering_files(*, root: Path, removed_files: Iterable[Path]) -> list[str]:
    """Return removed compatibility files that still exist in the repo."""
    return sorted(
        path.relative_to(root).as_posix() for path in removed_files if path.exists()
    )


def iter_compat_import_violations(
    *,
    ast_cache: Mapping[Path, ast.Module],
    root: Path,
    compat_modules: frozenset[str],
    compat_parent_imports: Mapping[str, frozenset[str]],
    allowed_files: frozenset[Path] = frozenset(),
) -> list[str]:
    """Return import violations for removed compatibility modules."""
    violations: list[str] = []
    for py_file, tree in sorted(ast_cache.items()):
        if py_file in allowed_files:
            continue
        rel_path = py_file.relative_to(root).as_posix()
        for node in ast.walk(tree):
            violations.extend(
                f"{rel_path}:{node.lineno} imports {compat_path}"
                for compat_path in _iter_node_compat_paths(
                    node=node,
                    compat_modules=compat_modules,
                    compat_parent_imports=compat_parent_imports,
                )
            )
    return violations


def _iter_node_compat_paths(
    *,
    node: ast.AST,
    compat_modules: frozenset[str],
    compat_parent_imports: Mapping[str, frozenset[str]],
) -> list[str]:
    if isinstance(node, ast.ImportFrom):
        return _iter_import_from_compat_paths(
            node=node,
            compat_modules=compat_modules,
            compat_parent_imports=compat_parent_imports,
        )
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names if alias.name in compat_modules]
    return []


def _iter_import_from_compat_paths(
    *,
    node: ast.ImportFrom,
    compat_modules: frozenset[str],
    compat_parent_imports: Mapping[str, frozenset[str]],
) -> list[str]:
    if node.module in compat_modules:
        return [node.module]
    if node.module not in compat_parent_imports:
        return []
    compat_children = compat_parent_imports[node.module]
    return [
        f"{node.module}.{alias.name}"
        for alias in node.names
        if alias.name in compat_children
    ]
