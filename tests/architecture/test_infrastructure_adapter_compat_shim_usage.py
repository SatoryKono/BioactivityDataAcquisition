"""Guardrails for infrastructure adapter compatibility shims."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMPAT_MODULES = frozenset(
    {
        "bioetl.infrastructure.adapters._error_classifier",
        "bioetl.infrastructure.adapters.chembl.fetch_mixin",
        "bioetl.infrastructure.adapters.openalex.client_helpers_mixin",
        "bioetl.infrastructure.adapters.uniprot.metadata_mixin",
    }
)
REMOVED_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "_error_classifier.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "chembl"
        / "fetch_mixin.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "openalex"
        / "client_helpers_mixin.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "uniprot"
        / "metadata_mixin.py",
    }
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.infrastructure.adapters": frozenset({"_error_classifier"}),
    "bioetl.infrastructure.adapters.chembl": frozenset({"fetch_mixin"}),
    "bioetl.infrastructure.adapters.openalex": frozenset({"client_helpers_mixin"}),
    "bioetl.infrastructure.adapters.uniprot": frozenset({"metadata_mixin"}),
}


def _iter_compat_import_violations(
    ast_cache: dict[Path, ast.Module],
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file, tree in sorted(ast_cache.items()):
        if py_file in allowed_files:
            continue
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
def test_infrastructure_adapter_compat_shim_files_have_been_removed() -> None:
    """Removed infrastructure adapter shim files should no longer exist."""
    lingering = sorted(
        path.relative_to(ROOT).as_posix() for path in REMOVED_FILES if path.exists()
    )
    assert not lingering, (
        "Infrastructure adapter compatibility shims must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_infrastructure_adapter_compat_shims_are_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import canonical adapter helpers directly."""
    violations = _iter_compat_import_violations(
        source_ast_cache,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Infrastructure adapter compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_infrastructure_adapter_compat_shims_are_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing removed adapter shim modules."""
    violations = _iter_compat_import_violations(
        test_ast_cache,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Infrastructure adapter compatibility shims must stay removed from tests:\n"
        + "\n".join(violations)
    )
