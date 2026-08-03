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
"""Guardrails for removed symbols on ``bioetl.composition.entrypoints``."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"
ENTRYPOINTS_MODULE = "bioetl.composition.entrypoints"
ENTRYPOINTS_FILE = SRC_ROOT / "composition" / "entrypoints.py"


def _legacy_entrypoint_symbols() -> set[str]:
    module = importlib.import_module(ENTRYPOINTS_MODULE)
    legacy_targets = getattr(module, "_LEGACY_SYMBOL_TARGETS", None)
    return set() if legacy_targets is None else set(legacy_targets)


def _iter_python_files() -> list[Path]:
    return [path for path in SRC_ROOT.rglob("*.py") if path != ENTRYPOINTS_FILE]


def _entrypoint_aliases_for_node(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Import):
        return _entrypoint_aliases_from_import(node)
    if isinstance(node, ast.ImportFrom):
        return _entrypoint_aliases_from_import_from(node)
    return set()


def _entrypoint_aliases(tree: ast.Module) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        aliases.update(_entrypoint_aliases_for_node(node))
    return aliases


def _entrypoint_aliases_from_import(node: ast.Import) -> set[str]:
    return {
        alias.asname or "entrypoints"
        for alias in node.names
        if alias.name == ENTRYPOINTS_MODULE
    }


def _entrypoint_aliases_from_import_from(node: ast.ImportFrom) -> set[str]:
    if node.module != "bioetl.composition":
        return set()
    return {
        alias.asname or alias.name
        for alias in node.names
        if alias.name == "entrypoints"
    }


def _deprecated_import_from_violations(
    path: Path, node: ast.ImportFrom, legacy_symbols: set[str]
) -> list[str]:
    if node.module != ENTRYPOINTS_MODULE:
        return []
    rel = path.relative_to(ROOT).as_posix()
    return [
        f"{rel}:{node.lineno}: {alias.name}"
        for alias in node.names
        if alias.name in legacy_symbols
    ]


def _deprecated_attribute_violation(
    path: Path,
    node: ast.Attribute,
    legacy_symbols: set[str],
    entrypoint_aliases: set[str],
) -> str | None:
    if not isinstance(node.value, ast.Name):
        return None
    if node.value.id not in entrypoint_aliases or node.attr not in legacy_symbols:
        return None
    rel = path.relative_to(ROOT).as_posix()
    return f"{rel}:{node.lineno}: {node.value.id}.{node.attr}"


def _deprecated_node_violations(
    path: Path,
    node: ast.AST,
    *,
    legacy_symbols: set[str],
    entrypoint_aliases: set[str],
) -> list[str]:
    if isinstance(node, ast.ImportFrom):
        return _deprecated_import_from_violations(path, node, legacy_symbols)
    if isinstance(node, ast.Attribute):
        violation = _deprecated_attribute_violation(
            path, node, legacy_symbols, entrypoint_aliases
        )
        return [] if violation is None else [violation]
    return []


def _deprecated_entrypoint_violations_for_path(
    path: Path, legacy_symbols: set[str]
) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    entrypoint_aliases = _entrypoint_aliases(tree)
    violations: list[str] = []
    for node in ast.walk(tree):
        violations.extend(
            _deprecated_node_violations(
                path,
                node,
                legacy_symbols=legacy_symbols,
                entrypoint_aliases=entrypoint_aliases,
            )
        )
    return violations


@pytest.mark.architecture
def test_first_party_src_does_not_import_deprecated_entrypoint_symbols() -> None:
    """Production code must not depend on removed entrypoint shims."""
    legacy_symbols = _legacy_entrypoint_symbols()
    assert legacy_symbols == set()
    if not legacy_symbols:
        return
    violations = [
        violation
        for path in _iter_python_files()
        for violation in _deprecated_entrypoint_violations_for_path(
            path, legacy_symbols
        )
    ]

    assert not violations, (
        "Removed bioetl.composition.entrypoints symbols leaked into first-party "
        "src. Import canonical owner APIs instead:\n" + "\n".join(sorted(violations))
    )
