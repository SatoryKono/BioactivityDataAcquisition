from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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
    vararg = getattr(func.args, "vararg", None)
    if vararg is not None and vararg.annotation is None:
        missing.append("param:*args")
    kwarg = getattr(func.args, "kwarg", None)
    if kwarg is not None and kwarg.annotation is None:
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
    with tempfile.TemporaryDirectory(prefix="mypy-cache-") as cache_dir:
        env = {**os.environ, "MYPY_CACHE_DIR": cache_dir}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "--config-file",
                "pyproject.toml",
                "--no-incremental",
                "src/bioetl",
            ],
            capture_output=True,
            text=True,
            env=env,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    if result.returncode != 0:
        output = (result.stdout + "\n" + result.stderr).strip()
        if "No module named mypy" in output or "mypy: command not found" in output:
            pytest.fail("mypy не найден. Установите зависимость: pip install mypy")
        pytest.fail(
            "mypy завершился с кодом "
            f"{result.returncode}\n"
            f"{result.stdout}\n"
            f"{result.stderr}"
        )
