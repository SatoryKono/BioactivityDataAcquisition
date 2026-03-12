"""Guardrails for pipeline/storage compatibility-only facade imports."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
COMPAT_MODULES = frozenset(
    {
        "bioetl.composition.factories.pipeline.facade",
        "bioetl.composition.factories.storage.facade",
        "bioetl.infrastructure.storage.delta_writer",
    }
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.composition.factories.pipeline": frozenset({"facade"}),
    "bioetl.composition.factories.storage": frozenset({"facade"}),
    "bioetl.infrastructure.storage": frozenset({"delta_writer"}),
}
ALLOWED_FILES = frozenset(
    {
        ROOT
        / "tests"
        / "architecture"
        / "test_deprecation_warnings.py",
        ROOT
        / "tests"
        / "unit"
        / "composition"
        / "factories"
        / "test_factory_decoupling_contracts.py",
        ROOT
        / "tests"
        / "unit"
        / "infrastructure"
        / "storage"
        / "test_delta_writer_compat.py",
    }
)


def _iter_compat_import_violations(search_root: Path) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in ALLOWED_FILES or "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in COMPAT_MODULES:
                rel_path = py_file.relative_to(ROOT).as_posix()
                violations.append(f"{rel_path}:{node.lineno} imports {node.module}")
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module in COMPAT_PARENT_IMPORTS
            ):
                compat_children = COMPAT_PARENT_IMPORTS[node.module]
                rel_path = py_file.relative_to(ROOT).as_posix()
                for alias in node.names:
                    if alias.name in compat_children:
                        compat_path = f"{node.module}.{alias.name}"
                        violations.append(
                            f"{rel_path}:{node.lineno} imports {compat_path}"
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in COMPAT_MODULES:
                        rel_path = py_file.relative_to(ROOT).as_posix()
                        violations.append(f"{rel_path}:{node.lineno} imports {alias.name}")
    return violations


@pytest.mark.architecture
def test_pipeline_storage_compat_shims_are_not_used_in_src() -> None:
    """First-party source code must import canonical pipeline/storage modules directly."""
    violations = _iter_compat_import_violations(SRC_ROOT)
    assert not violations, (
        "Pipeline/storage compatibility-only shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_pipeline_storage_compat_shims_are_only_used_by_dedicated_tests() -> None:
    """Ordinary tests must not accumulate new direct imports of compat-only modules."""
    violations = _iter_compat_import_violations(TESTS_ROOT)
    assert not violations, (
        "Pipeline/storage compatibility-only shims gained new direct test imports:\n"
        + "\n".join(violations)
    )
