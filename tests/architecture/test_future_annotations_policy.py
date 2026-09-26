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
"""Enforce the repository future-annotations policy for source modules.

The rule is intentionally strict for regular modules and only permits a tiny
set of package-level re-export facades to omit the import.
"""

from __future__ import annotations

import pytest

import ast
from pathlib import Path


pytestmark = pytest.mark.architecture

ALLOWED_MISSING_FUTURE_IMPORTS = {
    "domain/entities/bioactivity/__init__.py",
}


def _iter_effective_nodes(tree: ast.Module) -> list[ast.stmt]:
    """Return module statements excluding the leading docstring."""
    body = list(tree.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _has_future_annotations(tree: ast.Module) -> bool:
    """Return True when the first effective statement is the future import."""
    for node in _iter_effective_nodes(tree):
        return (
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(alias.name == "annotations" for alias in node.names)
        )
    return False


def _is_dunder_all_assignment(node: ast.stmt) -> bool:
    """Return True for ``__all__ = ...`` assignments."""
    if isinstance(node, ast.Assign):
        return (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
        )
    if isinstance(node, ast.AnnAssign):
        return isinstance(node.target, ast.Name) and node.target.id == "__all__"
    return False


def _is_reexport_only_package_facade(tree: ast.Module) -> bool:
    """Return True for a package facade with only re-exports and ``__all__``."""
    for node in _iter_effective_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            continue
        if _is_dunder_all_assignment(node):
            continue
        return False
    return True


def test_future_annotations_policy_is_enforced(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """All source modules must carry future annotations outside sanctioned facades."""
    bioetl_root = src_dir / "bioetl"
    missing_imports: set[str] = set()

    for path, tree in source_ast_cache.items():
        rel_path = path.relative_to(bioetl_root).as_posix()
        if not _has_future_annotations(tree):
            missing_imports.add(rel_path)

    disallowed_missing = sorted(missing_imports - ALLOWED_MISSING_FUTURE_IMPORTS)
    assert not disallowed_missing, (
        "Modules missing `from __future__ import annotations` outside the "
        "sanctioned package-facade exception:\n"
        + "\n".join(f"  - {path}" for path in disallowed_missing)
    )

    for rel_path in sorted(ALLOWED_MISSING_FUTURE_IMPORTS):
        path = bioetl_root / rel_path
        assert path.exists(), (
            f"Allowlisted future-annotations exception no longer exists: {rel_path}"
        )
        tree = source_ast_cache[path]
        assert path.name == "__init__.py", (
            f"Future-annotations exception must stay package-scoped: {rel_path}"
        )
        assert _is_reexport_only_package_facade(tree), (
            "Allowlisted future-annotations exception must remain a "
            f"re-export-only package facade: {rel_path}"
        )
