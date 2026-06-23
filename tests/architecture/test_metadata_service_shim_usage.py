"""Guardrails for metadata service compatibility shims."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_SHIM_MODULES = frozenset(
    {
        "bioetl.composition.services.metadata_coordinator",
        "bioetl.composition.services.metadata_assemblers",
    }
)
REMOVED_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "services"
        / "metadata_coordinator.py",
        ROOT / "src" / "bioetl" / "composition" / "services" / "metadata_assemblers.py",
    }
)


def _iter_shim_import_violations(
    ast_cache: dict[Path, ast.Module],
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file, tree in sorted(ast_cache.items()):
        if py_file in allowed_files:
            continue
        violations.extend(_iter_file_shim_import_violations(py_file, tree))
    return violations


def _iter_node_shim_paths(node: ast.AST) -> list[str]:
    if isinstance(node, ast.ImportFrom) and node.module in ALLOWED_SHIM_MODULES:
        return [node.module]
    if isinstance(node, ast.Import):
        return [
            alias.name for alias in node.names if alias.name in ALLOWED_SHIM_MODULES
        ]
    return []


def _iter_file_shim_import_violations(
    py_file: Path,
    tree: ast.AST,
) -> list[str]:
    rel_path = py_file.relative_to(ROOT).as_posix()
    return [
        f"{rel_path}:{node.lineno} imports {compat_path}"
        for node in ast.walk(tree)
        for compat_path in _iter_node_shim_paths(node)
    ]


@pytest.mark.architecture
def test_metadata_service_shim_files_have_been_removed() -> None:
    """Metadata composition shim files should no longer exist."""
    lingering = sorted(
        path.relative_to(ROOT).as_posix() for path in REMOVED_FILES if path.exists()
    )
    assert not lingering, (
        "Metadata service compatibility shims must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_metadata_service_shims_are_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party source code must import canonical metadata services directly."""
    violations = _iter_shim_import_violations(
        source_ast_cache,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Metadata service compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_metadata_service_shims_are_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing removed metadata shim modules."""
    violations = _iter_shim_import_violations(
        test_ast_cache,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Metadata service compatibility shims must stay removed from tests:\n"
        + "\n".join(violations)
    )
