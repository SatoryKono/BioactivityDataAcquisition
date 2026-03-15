"""Guardrails for application.core lifecycle compatibility shims."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
COMPAT_MODULES = frozenset(
    {
        "bioetl.application.core.checkpoint_manager",
        "bioetl.application.core.cleanup_service",
        "bioetl.application.core.heartbeat",
        "bioetl.application.core.lock_manager",
        "bioetl.application.core.shutdown",
    }
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.application.core": frozenset(
        {
            "checkpoint_manager",
            "cleanup_service",
            "heartbeat",
            "lock_manager",
            "shutdown",
        }
    ),
}
ALLOWED_TEST_FILES = frozenset(
    {
        ROOT
        / "tests"
        / "unit"
        / "application"
        / "core"
        / "test_lifecycle_shim_reexports.py",
    }
)


def _iter_compat_import_violations(search_root: Path) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in ALLOWED_TEST_FILES or "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        rel_path = py_file.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in COMPAT_MODULES:
                violations.append(f"{rel_path}:{node.lineno} imports {node.module}")
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module in COMPAT_PARENT_IMPORTS
            ):
                compat_children = COMPAT_PARENT_IMPORTS[node.module]
                for alias in node.names:
                    if alias.name in compat_children:
                        compat_path = f"{node.module}.{alias.name}"
                        violations.append(
                            f"{rel_path}:{node.lineno} imports {compat_path}"
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in COMPAT_MODULES:
                        violations.append(f"{rel_path}:{node.lineno} imports {alias.name}")
    return violations


@pytest.mark.architecture
def test_application_core_lifecycle_shims_are_not_used_in_src() -> None:
    """First-party src must import lifecycle implementations directly."""
    violations = _iter_compat_import_violations(SRC_ROOT)
    assert not violations, (
        "application.core lifecycle compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_application_core_lifecycle_shims_are_only_used_by_smoke_test() -> None:
    """Ordinary tests must not accumulate new direct imports of lifecycle shims."""
    violations = _iter_compat_import_violations(TESTS_ROOT)
    assert not violations, (
        "application.core lifecycle compatibility shims gained new direct test imports:\n"
        + "\n".join(violations)
    )
