"""Guardrails for application.core lifecycle compatibility shims."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMPAT_MODULES = frozenset(
    {
        "bioetl.application.core.checkpoint_manager",
        "bioetl.application.core.cleanup_service",
        "bioetl.application.core.heartbeat",
        "bioetl.application.core.lock_manager",
        "bioetl.application.core.shutdown",
    }
)
REMOVED_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "application" / "core" / "checkpoint_manager.py",
        ROOT / "src" / "bioetl" / "application" / "core" / "cleanup_service.py",
        ROOT / "src" / "bioetl" / "application" / "core" / "heartbeat.py",
        ROOT / "src" / "bioetl" / "application" / "core" / "lock_manager.py",
        ROOT / "src" / "bioetl" / "application" / "core" / "shutdown.py",
    }
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.application.core": frozenset(
        {
            "checkpoint_manager",
            "cleanup_service",
            "heartbeat",
            "lock_manager",
            "shutdown",
        }
    ),
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
        return [alias.name for alias in node.names if alias.name in COMPAT_MODULES]
    return []


def _iter_import_from_compat_paths(node: ast.ImportFrom) -> list[str]:
    if node.module in COMPAT_MODULES:
        return [node.module]
    if node.module not in COMPAT_PARENT_IMPORTS:
        return []
    compat_children = COMPAT_PARENT_IMPORTS[node.module]
    return [
        f"{node.module}.{alias.name}"
        for alias in node.names
        if alias.name in compat_children
    ]


@pytest.mark.architecture
def test_application_core_lifecycle_shim_files_have_been_removed() -> None:
    """Lifecycle compatibility shim files should no longer exist."""
    lingering = sorted(
        path.relative_to(ROOT).as_posix() for path in REMOVED_FILES if path.exists()
    )
    assert not lingering, (
        "application.core lifecycle compatibility shims must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_application_core_lifecycle_shims_are_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import lifecycle implementations directly."""
    violations = _iter_compat_import_violations(source_ast_cache)
    assert not violations, (
        "application.core lifecycle compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_application_core_lifecycle_shims_are_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing removed lifecycle shim modules."""
    violations = _iter_compat_import_violations(test_ast_cache)
    assert not violations, (
        "application.core lifecycle compatibility shims must stay removed from tests:\n"
        + "\n".join(violations)
    )
