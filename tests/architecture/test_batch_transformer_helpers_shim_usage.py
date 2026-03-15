"""Guardrails for batch_transformer_helpers compatibility shim."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
COMPAT_MODULE = "bioetl.application.core.batch_transformer_helpers"
REMOVED_FILE = (
    ROOT / "src" / "bioetl" / "application" / "core" / "batch_transformer_helpers.py"
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.application.core": frozenset({"batch_transformer_helpers"}),
}


def _iter_compat_import_violations(search_root: Path) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        rel_path = py_file.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == COMPAT_MODULE:
                violations.append(f"{rel_path}:{node.lineno} imports {COMPAT_MODULE}")
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
                    if alias.name == COMPAT_MODULE:
                        violations.append(f"{rel_path}:{node.lineno} imports {alias.name}")
    return violations


@pytest.mark.architecture
def test_batch_transformer_helpers_shim_file_has_been_removed() -> None:
    """The batch_transformer_helpers compatibility module should no longer exist."""
    assert not REMOVED_FILE.exists(), (
        "batch_transformer_helpers compatibility shim must stay removed: "
        "src/bioetl/application/core/batch_transformer_helpers.py"
    )


@pytest.mark.architecture
def test_batch_transformer_helpers_shim_is_not_used_in_src() -> None:
    """First-party src must import canonical batch-transform helper modules directly."""
    violations = _iter_compat_import_violations(SRC_ROOT)
    assert not violations, (
        "batch_transformer_helpers compatibility shim is still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_batch_transformer_helpers_shim_is_not_used_in_tests() -> None:
    """Tests must not keep importing the removed helper shim."""
    violations = _iter_compat_import_violations(TESTS_ROOT)
    assert not violations, (
        "batch_transformer_helpers compatibility shim must stay removed from tests:\n"
        + "\n".join(violations)
    )
