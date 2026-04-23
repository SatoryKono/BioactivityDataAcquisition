"""Ratchet tests for ChEMBL finite-vocabulary externalization."""

from __future__ import annotations

import ast
from pathlib import Path

PROFILE_DIR = Path("src/bioetl/domain/normalization/profiles")


def _enum_value_nodes(tree: ast.AST) -> list[ast.AST]:
    values: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_ENUM_FIELDS"
            for target in node.targets
        ):
            if isinstance(node.value, ast.Dict):
                values.extend(node.value.values)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "build_standard_profile"
        ):
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
