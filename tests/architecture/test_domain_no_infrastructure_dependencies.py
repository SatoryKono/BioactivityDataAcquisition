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
"""Guard the domain layer against infrastructure imports.

The existing layer tests cover several import-matrix edges, but this suite
keeps the ``domain -> infrastructure`` rule explicit and fail-closed:

- direct ``import`` / ``from ... import ...`` statements are forbidden
- imports nested under ``if TYPE_CHECKING`` are still forbidden
- string-literal dynamic imports via ``import_module`` / ``__import__`` are forbidden
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

FORBIDDEN_PREFIX = "bioetl.infrastructure"
IMPORT_HELPER_NAMES = {"import_module", "_import_module", "__import__"}


def _iter_domain_modules(
    *,
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
) -> list[tuple[Path, ast.Module]]:
    domain_root = src_dir / "bioetl" / "domain"
    assert domain_root.exists(), f"Domain layer not found: {domain_root}"
    return sorted(
        (
            (path, tree)
            for path, tree in source_ast_cache.items()
            if domain_root in path.parents
        ),
        key=lambda item: item[0],
    )


def _matches_forbidden_module(module_name: str | None) -> bool:
    if module_name is None:
        return False
    return module_name == FORBIDDEN_PREFIX or module_name.startswith(
        FORBIDDEN_PREFIX + "."
    )


def _call_target_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _string_literal_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    first_arg = node.args[0]
    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
        return first_arg.value
    return None


def _import_violations(node: ast.Import, *, rel_path: Path) -> list[str]:
    return [
        f"{rel_path}:{node.lineno} imports {alias.name}"
        for alias in node.names
        if _matches_forbidden_module(alias.name)
    ]


def _import_from_violations(node: ast.ImportFrom, *, rel_path: Path) -> list[str]:
    if not _matches_forbidden_module(node.module):
        return []
    module_name = node.module or "<relative>"
    return [f"{rel_path}:{node.lineno} imports from {module_name}"]


def _dynamic_import_violations(node: ast.Call, *, rel_path: Path) -> list[str]:
    helper_name = _call_target_name(node)
    if helper_name not in IMPORT_HELPER_NAMES:
        return []
    import_target = _string_literal_arg(node)
    if not _matches_forbidden_module(import_target):
        return []
    return [f"{rel_path}:{node.lineno} dynamically imports {import_target}"]


def _module_import_violations(
    *,
    py_file: Path,
    tree: ast.Module,
    src_dir: Path,
) -> list[str]:
    rel_path = py_file.relative_to(src_dir)
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(_import_violations(node, rel_path=rel_path))
            continue

        if isinstance(node, ast.ImportFrom):
            violations.extend(_import_from_violations(node, rel_path=rel_path))
            continue

        if isinstance(node, ast.Call):
            violations.extend(_dynamic_import_violations(node, rel_path=rel_path))

    return violations


@pytest.mark.architecture
def test_domain_layer_contains_no_infrastructure_dependencies(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """REQ-ARCH-DOM-001: Domain must not import infrastructure dependencies."""
    violations = [
        violation
        for py_file, tree in _iter_domain_modules(
            src_dir=src_dir,
            source_ast_cache=source_ast_cache,
        )
        for violation in _module_import_violations(
            py_file=py_file,
            tree=tree,
            src_dir=src_dir,
        )
    ]

    assert not violations, (
        "Domain layer must not depend on infrastructure modules, including "
        "TYPE_CHECKING-only or dynamic import paths.\n"
        + "\n".join(f"  - {violation}" for violation in violations[:100])
    )
