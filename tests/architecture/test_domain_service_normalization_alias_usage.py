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
"""Freeze guard for deprecated domain service normalization compatibility seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LEGACY_SERVICE_MODULES = frozenset(
    {
        "bioetl.domain.services._date_helpers",
        "bioetl.domain.services.date_normalization",
        "bioetl.domain.services.doi_normalization",
        "bioetl.domain.services.pmid_normalization",
        "bioetl.domain.services.text_normalization",
    }
)
LEGACY_SERVICE_PARENT_IMPORTS = {
    "bioetl.domain.services": frozenset(
        {
            "DateBioactivityNormalizer",
            "DoiBioactivityNormalizer",
            "PmidBioactivityNormalizer",
            "TextBioactivityNormalizer",
        }
    )
}
ALLOWED_SRC_FILES: frozenset[Path] = frozenset()


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
            violations.extend(_service_import_from_violations(node, rel_path))
            violations.extend(_service_import_violations(node, rel_path))
    return violations


def _service_import_from_violations(node: ast.AST, rel_path: str) -> list[str]:
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.module in LEGACY_SERVICE_MODULES:
        return [f"{rel_path}:{node.lineno} imports {node.module}"]
    if node.module not in LEGACY_SERVICE_PARENT_IMPORTS:
        return []

    compat_children = LEGACY_SERVICE_PARENT_IMPORTS[node.module]
    return [
        f"{rel_path}:{node.lineno} imports {node.module}.{alias.name}"
        for alias in node.names
        if alias.name in compat_children
    ]


def _service_import_violations(node: ast.AST, rel_path: str) -> list[str]:
    if not isinstance(node, ast.Import):
        return []
    return [
        f"{rel_path}:{node.lineno} imports {alias.name}"
        for alias in node.names
        if alias.name in LEGACY_SERVICE_MODULES
    ]


@pytest.mark.architecture
def test_deprecated_domain_service_normalization_shims_are_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Repo source must use canonical normalization helpers instead."""
    violations = _iter_compat_import_violations(
        source_ast_cache,
        allowed_files=ALLOWED_SRC_FILES,
    )
    assert not violations, (
        "Deprecated domain service normalization shims are still imported from src/:\n"
        + "\n".join(violations)
        + "\n\nUse bioetl.domain.normalization.* directly instead."
    )


@pytest.mark.architecture
def test_deprecated_domain_service_normalization_shims_are_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests should exercise the canonical normalization helpers directly."""
    violations = _iter_compat_import_violations(
        test_ast_cache,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Deprecated domain service normalization shims are still imported from tests/:\n"
        + "\n".join(violations)
        + "\n\nUse bioetl.domain.normalization.* directly instead."
    )
