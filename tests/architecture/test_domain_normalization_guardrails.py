"""Architecture guardrails for the domain normalization package.

`domain.normalization.*` is the canonical home for deterministic, pure
normalization logic. These tests keep that package free from infrastructure,
I/O, dataframe libraries, and back-sliding to service-layer helpers.
"""

from __future__ import annotations

import ast
from pathlib import Path


_NORMALIZATION_PACKAGE_PREFIX = "bioetl/domain/normalization/"
_NORMALIZATION_COMPAT_MODULES = {
    "bioetl/domain/normalization_authors.py",
    "bioetl/domain/normalization_chembl.py",
    "bioetl/domain/normalization_dates.py",
    "bioetl/domain/normalization_pages.py",
}

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


def _disallowed_import_violations_for_node(
    node: ast.AST,
    *,
    relative: Path,
) -> list[str]:
    violations: list[str] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            for prefix, reason in _DISALLOWED_IMPORT_PREFIXES.items():
                if _matches_prefix(alias.name, prefix):
                    violations.append(
                        f"{relative}:{node.lineno}: import {alias.name} ({reason})"
                    )
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        for prefix, reason in _DISALLOWED_IMPORT_PREFIXES.items():
            if _matches_prefix(node.module, prefix):
                violations.append(
                    f"{relative}:{node.lineno}: from {node.module} import ..."
                    f" ({reason})"
                )
    return violations


def _iter_disallowed_imports(
    source_ast_cache: dict[Path, ast.Module],
    src_dir: Path,
) -> list[str]:
    """Collect disallowed imports from normalization runtime modules."""
    violations: list[str] = []

    for relative, tree in _iter_normalization_modules(source_ast_cache, src_dir):
        parents = _build_parent_map(tree)
        for node in ast.walk(tree):
            if _is_inside_type_checking(node, parents):
                continue
            violations.extend(
                _disallowed_import_violations_for_node(
                    node,
                    relative=relative,
                )
            )

    return violations


def _iter_open_calls(
    source_ast_cache: dict[Path, ast.Module],
    src_dir: Path,
) -> list[str]:
    """Collect direct `open(...)` calls from normalization runtime modules."""
    violations: list[str] = []

    for relative, tree in _iter_normalization_modules(source_ast_cache, src_dir):
        parents = _build_parent_map(tree)
        for node in ast.walk(tree):
            if _is_inside_type_checking(node, parents):
                continue
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                violations.append(f"{relative}:{node.lineno}: open(...)")

    return violations


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
