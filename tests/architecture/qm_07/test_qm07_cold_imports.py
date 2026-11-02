"""Core runtime must never depend on repository engineering modules."""

from __future__ import annotations
import ast
from pathlib import Path
import pytest

pytestmark = pytest.mark.architecture


def test_runtime_has_no_engineering_imports() -> None:
    root = Path(__file__).resolve().parents[3]
    violations: list[str] = []
    for path in (root / "src/bioetl").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            elif isinstance(node, ast.Call) and node.args:
                function = node.func
                is_loader = (
                    isinstance(function, ast.Name) and function.id == "__import__"
                ) or (
                    isinstance(function, ast.Attribute)
                    and function.attr == "import_module"
                )
                if (
                    is_loader
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    modules = [node.args[0].value]
            for module in modules:
                if module == "scripts" or module.startswith("scripts."):
                    violations.append(
                        f"{path.relative_to(root)}:{node.lineno}:{module}"
                    )
    assert violations == []
