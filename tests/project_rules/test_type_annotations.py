from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

import pytest

from tests.project_rules.conftest import iter_python_files

SKIP_ARGS = {"self", "cls"}


def _iter_functions(tree: ast.AST) -> Iterable[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _missing_annotations(func: ast.AST) -> list[str]:
    missing: list[str] = []
    args = func.args.args + func.args.kwonlyargs
    for arg in args:
        if arg.arg in SKIP_ARGS:
            continue
        if arg.annotation is None:
            missing.append(f"param:{arg.arg}")
    if getattr(func.args, "vararg", None) and func.args.vararg.annotation is None:
        missing.append("param:*args")
    if getattr(func.args, "kwarg", None) and func.args.kwarg.annotation is None:
        missing.append("param:**kwargs")
    if getattr(func, "returns", None) is None:
        missing.append("return")
    return missing


def test_public_functions_are_annotated(bioetl_root: Path) -> None:
    violations: list[str] = []
    for path in iter_python_files(bioetl_root):
        code = path.read_text(encoding="utf-8")
        tree = ast.parse(code)
        for func in _iter_functions(tree):
            name = func.name
            if name.startswith("_"):
                continue
            missing = _missing_annotations(func)
            if missing:
                violations.append(
                    f"{path.as_posix()}:{func.lineno}: отсутствуют аннотации {missing}"
                )
    if violations:
        pytest.fail("\n".join(sorted(set(violations))))


def test_mypy_strict_available() -> None:
    if shutil.which("mypy") is None:
        pytest.skip("mypy не установлен")
    result = subprocess.run(
        ["mypy", "--config-file", "pyproject.toml", "src/bioetl"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            f"mypy завершился с кодом {result.returncode}\n"
            f"{result.stdout}\n{result.stderr}"
        )

