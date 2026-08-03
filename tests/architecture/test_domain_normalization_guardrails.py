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
"""Architecture guardrails for the domain normalization package.

`domain.normalization.*` is the canonical home for deterministic, pure
normalization logic. These tests keep that package free from infrastructure,
I/O, dataframe libraries, and back-sliding to service-layer helpers.
"""

from __future__ import annotations

import pytest

import ast
from pathlib import Path
from collections.abc import Callable


pytestmark = pytest.mark.architecture

_NORMALIZATION_PACKAGE_PREFIX = "bioetl/domain/normalization/"
_NORMALIZATION_COMPAT_MODULES: set[str] = set()

_DISALLOWED_IMPORT_PREFIXES: dict[str, str] = {
    "bioetl.infrastructure": "normalization logic must not depend on infrastructure",
    "bioetl.domain.services": "normalization logic must live in domain.normalization.*",
    "pandas": "normalization helpers must remain dataframe-free",
    "pyarrow": "normalization helpers must remain arrow-free",
    "httpx": "normalization helpers must not perform network I/O",
    "structlog": "normalization helpers must not depend on logging backends",
    "requests": "normalization helpers must not perform network I/O",
    "pathlib": "normalization helpers must not perform filesystem I/O",
    "io": "normalization helpers must not perform stream I/O",
}


def _iter_normalization_modules(
    source_ast_cache: dict[Path, ast.Module],
    src_dir: Path,
) -> list[tuple[Path, ast.Module]]:
    """Return source AST entries that belong to normalization runtime modules."""
    targets: list[tuple[Path, ast.Module]] = []
    for path, tree in sorted(source_ast_cache.items()):
        relative = path.relative_to(src_dir)
        relative_posix = relative.as_posix()
        if relative_posix.startswith(_NORMALIZATION_PACKAGE_PREFIX):
            targets.append((relative, tree))
            continue
        if relative_posix in _NORMALIZATION_COMPAT_MODULES:
            targets.append((relative, tree))
    return targets


def _is_type_checking_guard(test: ast.expr) -> bool:
    """Return True when an AST expression represents TYPE_CHECKING."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute) and isinstance(test.value, ast.Name):
        return test.value.id == "typing" and test.attr == "TYPE_CHECKING"
    return False


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    """Build a parent lookup map for AST nodes."""
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def _is_inside_type_checking(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    """Return True if the node is nested beneath `if TYPE_CHECKING:`."""
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.If) and _is_type_checking_guard(current.test):
            return True
        current = parents.get(current)
    return False


def _matches_prefix(module_name: str, prefix: str) -> bool:
    """Return True if `module_name` is equal to or nested under `prefix`."""
    return module_name == prefix or module_name.startswith(f"{prefix}.")


def _matched_disallowed_reason(module_name: str) -> str | None:
    return next(
        (
            reason
            for prefix, reason in _DISALLOWED_IMPORT_PREFIXES.items()
            if _matches_prefix(module_name, prefix)
        ),
        None,
    )


def _import_violation(relative: Path, lineno: int, module_name: str) -> str:
    reason = _matched_disallowed_reason(module_name)
    if reason is None:
        return ""
    return f"{relative}:{lineno}: import {module_name} ({reason})"


def _import_from_violation(relative: Path, lineno: int, module_name: str) -> str:
    reason = _matched_disallowed_reason(module_name)
    if reason is None:
        return ""
    return f"{relative}:{lineno}: from {module_name} import ... ({reason})"


def _disallowed_import_violations_for_node(
    node: ast.AST,
    *,
    relative: Path,
) -> list[str]:
    if isinstance(node, ast.Import):
        return [
            violation
            for alias in node.names
            if (violation := _import_violation(relative, node.lineno, alias.name))
        ]
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        violation = _import_from_violation(relative, node.lineno, node.module)
        return [violation] if violation else []
    return []


def _runtime_nodes(tree: ast.Module) -> list[ast.AST]:
    parents = _build_parent_map(tree)
    return [
        node for node in ast.walk(tree) if not _is_inside_type_checking(node, parents)
    ]


def _runtime_module_violations(
    source_ast_cache: dict[Path, ast.Module],
    src_dir: Path,
    collector: Callable[[ast.AST, Path], list[str]],
) -> list[str]:
    violations: list[str] = []
    for relative, tree in _iter_normalization_modules(source_ast_cache, src_dir):
        for node in _runtime_nodes(tree):
            violations.extend(collector(node, relative))
    return violations


def _iter_disallowed_imports(
    source_ast_cache: dict[Path, ast.Module],
    src_dir: Path,
) -> list[str]:
    """Collect disallowed imports from normalization runtime modules."""
    return _runtime_module_violations(
        source_ast_cache,
        src_dir,
        lambda node, relative: _disallowed_import_violations_for_node(
            node,
            relative=relative,
        ),
    )


def _open_call_violations(node: ast.AST, relative: Path) -> list[str]:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
    ):
        return [f"{relative}:{node.lineno}: open(...)"]
    return []


def _iter_open_calls(
    source_ast_cache: dict[Path, ast.Module],
    src_dir: Path,
) -> list[str]:
    """Collect direct `open(...)` calls from normalization runtime modules."""
    return _runtime_module_violations(
        source_ast_cache,
        src_dir,
        _open_call_violations,
    )


def test_domain_normalization_modules_have_no_disallowed_runtime_imports(
    source_ast_cache: dict[Path, ast.Module],
    src_dir: Path,
) -> None:
    """Normalization modules must stay pure and independent from infra/I/O libs."""
    violations = _iter_disallowed_imports(source_ast_cache, src_dir)

    assert not violations, (
        "domain.normalization runtime modules import forbidden dependencies:\n"
        + "\n".join(f"  - {violation}" for violation in violations)
        + "\n\nNormalization helpers must remain pure, deterministic, and free of "
        "infrastructure, service-layer, dataframe, logging, and I/O dependencies."
    )


def test_domain_normalization_modules_do_not_call_open(
    source_ast_cache: dict[Path, ast.Module],
    src_dir: Path,
) -> None:
    """Normalization modules must not perform filesystem I/O via `open`."""
    violations = _iter_open_calls(source_ast_cache, src_dir)

    assert not violations, (
        "domain.normalization runtime modules must not perform file I/O:\n"
        + "\n".join(f"  - {violation}" for violation in violations)
    )
