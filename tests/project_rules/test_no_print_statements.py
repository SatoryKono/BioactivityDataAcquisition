from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.project_rules.conftest import iter_python_files


def _has_print_call(tree: ast.AST) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "print":
                lines.append(node.lineno)
    return lines


def test_no_print_in_production(bioetl_root: Path) -> None:
    violations: list[str] = []
    for path in iter_python_files(bioetl_root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        lines = _has_print_call(tree)
        for lineno in lines:
            violations.append(f"{path.as_posix()}:{lineno}: запрет print()")

    if violations:
        pytest.fail("\n".join(sorted(set(violations))))

