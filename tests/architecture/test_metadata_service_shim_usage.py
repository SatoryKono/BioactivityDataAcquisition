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
REMOVED_FILES = frozenset(
    {
        ROOT / "src" / "bioetl" / "composition" / "services" / "metadata_coordinator.py",
        ROOT / "src" / "bioetl" / "composition" / "services" / "metadata_assemblers.py",
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
def test_metadata_service_shim_files_have_been_removed() -> None:
    """Metadata composition shim files should no longer exist."""
    lingering = sorted(
        path.relative_to(ROOT).as_posix() for path in REMOVED_FILES if path.exists()
    )
    assert not lingering, (
        "Metadata service compatibility shims must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_metadata_service_shims_are_not_used_in_src() -> None:
    """First-party source code must import canonical metadata services directly."""
    violations = _iter_shim_import_violations(
        SRC_ROOT,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Metadata service compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_metadata_service_shims_are_not_used_in_tests() -> None:
    """Tests must not keep importing removed metadata shim modules."""
    violations = _iter_shim_import_violations(
        TESTS_ROOT,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Metadata service compatibility shims must stay removed from tests:\n"
        + "\n".join(violations)
    )
