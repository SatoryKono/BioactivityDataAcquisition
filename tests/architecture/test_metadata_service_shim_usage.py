"""Guardrails for metadata service compatibility shims."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
ALLOWED_SHIM_MODULES = frozenset(
    {
        "bioetl.composition.services.metadata_coordinator",
        "bioetl.composition.services.metadata_assemblers",
    }
)
ALLOWED_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "composition" / "services" / "metadata_coordinator.py",
        ROOT / "src" / "bioetl" / "composition" / "services" / "metadata_assemblers.py",
    }
)
ALLOWED_TEST_FILES = frozenset(
    {
        ROOT
        / "tests"
        / "unit"
        / "composition"
        / "services"
        / "test_metadata_coordinator_reexport.py",
        ROOT
        / "tests"
        / "unit"
        / "composition"
        / "services"
        / "test_metadata_assemblers_reexport.py",
    }
)


def _iter_shim_import_violations(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in ALLOWED_SHIM_MODULES:
                rel_path = py_file.relative_to(ROOT).as_posix()
                violations.append(
                    f"{rel_path}:{node.lineno} imports {node.module}"
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ALLOWED_SHIM_MODULES:
                        rel_path = py_file.relative_to(ROOT).as_posix()
                        violations.append(
                            f"{rel_path}:{node.lineno} imports {alias.name}"
                        )
    return violations


@pytest.mark.architecture
def test_metadata_service_shims_are_not_used_in_src() -> None:
    """First-party source code must import canonical metadata services directly."""
    violations = _iter_shim_import_violations(
        SRC_ROOT,
        allowed_files=ALLOWED_FILES,
    )
    assert not violations, (
        "Metadata service compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_metadata_service_shims_are_only_used_by_dedicated_smoke_tests() -> None:
    """Ordinary tests must not accumulate new direct imports of metadata shims."""
    violations = _iter_shim_import_violations(
        TESTS_ROOT,
        allowed_files=ALLOWED_TEST_FILES,
    )
    assert not violations, (
        "Metadata service compatibility shims gained new non-smoke test imports:\n"
        + "\n".join(violations)
    )
