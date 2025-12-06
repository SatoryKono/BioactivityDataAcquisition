from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

PACKAGE_ROOT = Path("src") / "bioetl"
CONFIG_ROOT = Path("configs")


def _iter_python_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and path.is_file()
    ]


def test_public_definitions_have_docstrings() -> None:
    """All public functions and classes must document their purpose."""

    violations: list[str] = []
    for path in _iter_python_files(PACKAGE_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_"):
                    continue
                if ast.get_docstring(node) is None:
                    violations.append(f"{path.as_posix()}: {node.name}")

    if violations:
        pytest.fail(
            "Missing docstrings detected:\n" + "\n".join(sorted(set(violations)))
        )


def test_naming_conventions() -> None:
    """Validate class and function naming against project regex rules."""

    class_pattern = re.compile(r"^[A-Z][A-Za-z0-9]+$")
    func_pattern = re.compile(r"^[a-z_][a-z0-9_]*$")

    violations: list[str] = []
    for path in _iter_python_files(PACKAGE_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("_"):
                    continue
                if not class_pattern.match(node.name):
                    violations.append(f"{path.as_posix()}: class {node.name}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                if not func_pattern.match(node.name):
                    violations.append(f"{path.as_posix()}: function {node.name}")

    if violations:
        pytest.fail(
            "Naming convention violations:\n" + "\n".join(sorted(set(violations)))
        )


def test_no_builtin_print_usage() -> None:
    """Ensure production code relies on logging instead of print()."""

    violations: list[str] = []
    for path in _iter_python_files(PACKAGE_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "print":
                    violations.append(f"{path.as_posix()}: line {node.lineno}")

    if violations:
        pytest.fail(
            "Forbidden print() calls found:\n" + "\n".join(sorted(set(violations)))
        )


def test_configs_are_well_formed_yaml() -> None:
    """All YAML configs must be syntactically valid and loadable."""

    yaml_files = [path for path in CONFIG_ROOT.rglob("*.yml")]
    yaml_files.extend(path for path in CONFIG_ROOT.rglob("*.yaml"))

    allowed_empty = {CONFIG_ROOT / "profiles" / "high_timeout.yaml"}

    if not yaml_files:
        pytest.skip("No YAML configs discovered.")

    failures: list[str] = []
    for path in yaml_files:
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:  # pragma: no cover - defensive
            failures.append(f"{path.as_posix()}: {exc}")
            continue

        if loaded is None and path not in allowed_empty:
            failures.append(f"{path.as_posix()}: YAML parsed as empty content")

    if failures:
        pytest.fail("Invalid YAML configs:\n" + "\n".join(sorted(failures)))
