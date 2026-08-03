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
"""Freeze guard for legacy domain normalization compatibility modules."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LEGACY_NORMALIZATION_MODULES = frozenset(
    {
        "bioetl.domain.normalization_authors",
        "bioetl.domain.normalization_chembl",
        "bioetl.domain.normalization_dates",
        "bioetl.domain.normalization_pages",
    }
)
LEGACY_PARENT_IMPORTS = {
    "bioetl.domain": frozenset(
        {
            "normalization_authors",
            "normalization_chembl",
            "normalization_dates",
            "normalization_pages",
        }
    )
}


def _iter_compat_import_violations(
    ast_cache: dict[Path, ast.Module],
) -> list[str]:
    violations: list[str] = []
    for py_file, tree in sorted(ast_cache.items()):
        rel_path = py_file.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            violations.extend(_import_from_violations(node, rel_path))
            violations.extend(_import_violations(node, rel_path))
    return violations


def _import_from_violations(node: ast.AST, rel_path: str) -> list[str]:
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.module in LEGACY_NORMALIZATION_MODULES:
        return [f"{rel_path}:{node.lineno} imports {node.module}"]
    if node.module not in LEGACY_PARENT_IMPORTS:
        return []

    compat_children = LEGACY_PARENT_IMPORTS[node.module]
    return [
        f"{rel_path}:{node.lineno} imports {node.module}.{alias.name}"
        for alias in node.names
        if alias.name in compat_children
    ]


def _import_violations(node: ast.AST, rel_path: str) -> list[str]:
    if not isinstance(node, ast.Import):
        return []
    return [
        f"{rel_path}:{node.lineno} imports {alias.name}"
        for alias in node.names
        if alias.name in LEGACY_NORMALIZATION_MODULES
    ]


@pytest.mark.architecture
def test_legacy_domain_normalization_compat_modules_are_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Runtime source must import canonical normalization package directly."""
    violations = _iter_compat_import_violations(source_ast_cache)
    assert not violations, (
        "Legacy domain normalization compatibility modules are still imported from src/:\n"
        + "\n".join(violations)
        + "\n\nUse bioetl.domain.normalization or bioetl.domain.normalization.* instead."
    )


@pytest.mark.architecture
def test_legacy_domain_normalization_compat_modules_are_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must also exercise the canonical normalization surface."""
    violations = _iter_compat_import_violations(test_ast_cache)
    assert not violations, (
        "Legacy domain normalization compatibility modules are still imported from tests/:\n"
        + "\n".join(violations)
        + "\n\nUse bioetl.domain.normalization or bioetl.domain.normalization.* instead."
    )
