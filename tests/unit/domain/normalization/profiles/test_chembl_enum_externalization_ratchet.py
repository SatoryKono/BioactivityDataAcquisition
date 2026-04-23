"""Ratchet tests for ChEMBL finite-vocabulary externalization."""

from __future__ import annotations

import ast
from pathlib import Path

PROFILE_DIR = Path("src/bioetl/domain/normalization/profiles")


def _enum_value_nodes(tree: ast.AST) -> list[ast.AST]:
    values: list[ast.AST] = []
    for node in ast.walk(tree):
        values.extend(_assigned_enum_value_nodes(node))
        values.extend(_profile_enum_value_nodes(node))
    return values


def _assigned_enum_value_nodes(node: ast.AST) -> list[ast.AST]:
    """Return inline enum value nodes from module-level _ENUM_FIELDS assignments."""
    if not isinstance(node, ast.Assign) or not any(
        isinstance(target, ast.Name) and target.id == "_ENUM_FIELDS"
        for target in node.targets
    ):
        return []
    if not isinstance(node.value, ast.Dict):
        return []
    return list(node.value.values)


def _profile_enum_value_nodes(node: ast.AST) -> list[ast.AST]:
    """Return inline enum value nodes passed to build_standard_profile()."""
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_standard_profile"
    ):
        return []
    values: list[ast.AST] = []
    for keyword in node.keywords:
        if keyword.arg == "enum_fields" and isinstance(keyword.value, ast.Dict):
            values.extend(keyword.value.values)
    return values


def _is_inline_finite_literal(node: ast.AST) -> bool:
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        return True
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"frozenset", "set"}
        and node.args
        and isinstance(node.args[0], (ast.Set, ast.List, ast.Tuple))
    ):
        return True
    return False


def test_chembl_profile_enum_values_do_not_ship_as_inline_literals() -> None:
    violations: list[str] = []

    for path in sorted(PROFILE_DIR.glob("chembl_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for value_node in _enum_value_nodes(tree):
            if _is_inline_finite_literal(value_node):
                violations.append(f"{path.name}:{getattr(value_node, 'lineno', '?')}")

    assert violations == []
