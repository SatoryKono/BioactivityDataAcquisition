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
REMOVED_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "application" / "core" / "checkpoint_manager.py",
        ROOT / "src" / "bioetl" / "application" / "core" / "cleanup_service.py",
        ROOT / "src" / "bioetl" / "application" / "core" / "heartbeat.py",
        ROOT / "src" / "bioetl" / "application" / "core" / "lock_manager.py",
        ROOT / "src" / "bioetl" / "application" / "core" / "shutdown.py",
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


def _iter_compat_import_violations(search_root: Path) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
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
                        violations.append(
                            f"{rel_path}:{node.lineno} imports {alias.name}"
                        )
    return violations


@pytest.mark.architecture
def test_application_core_lifecycle_shim_files_have_been_removed() -> None:
    """Lifecycle compatibility shim files should no longer exist."""
    lingering = sorted(
        path.relative_to(ROOT).as_posix() for path in REMOVED_FILES if path.exists()
    )
    assert not lingering, (
        "application.core lifecycle compatibility shims must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_application_core_lifecycle_shims_are_not_used_in_src() -> None:
    """First-party src must import lifecycle implementations directly."""
    violations = _iter_compat_import_violations(SRC_ROOT)
    assert not violations, (
        "application.core lifecycle compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_application_core_lifecycle_shims_are_not_used_in_tests() -> None:
    """Tests must not keep importing removed lifecycle shim modules."""
    violations = _iter_compat_import_violations(TESTS_ROOT)
    assert not violations, (
        "application.core lifecycle compatibility shims must stay removed from tests:\n"
        + "\n".join(violations)
    )
