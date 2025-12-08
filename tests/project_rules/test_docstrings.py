from __future__ import annotations

import ast
from pathlib import Path
from typing import Mapping, Set

import pytest

from tests.project_rules.conftest import iter_python_files

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_MISSING_DOCSTRINGS: Mapping[str, Set[str]] = {
    "src/bioetl/domain/configs/pipeline.py": {
        "rest_interface_enabled",
        "mq_interface_enabled",
    },
}


def test_public_symbols_have_docstrings(bioetl_root: Path) -> None:
    violations: list[str] = []
    for path in iter_python_files(bioetl_root):
        rel_path = path.relative_to(PROJECT_ROOT).as_posix()
        allowed_names = ALLOWED_MISSING_DOCSTRINGS.get(rel_path, set())

        code = path.read_text(encoding="utf-8")
        tree = ast.parse(code)

        module_doc = ast.get_docstring(tree)
        if module_doc is None:
            violations.append(f"{path.as_posix()}: отсутствует module docstring")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                if name.startswith("_") or name in allowed_names:
                    continue
                if ast.get_docstring(node) is None:
                    violations.append(
                        f"{path.as_posix()}:{node.lineno}: {name} без docstring"
                    )

    if violations:
        pytest.fail("\n".join(sorted(set(violations))))
