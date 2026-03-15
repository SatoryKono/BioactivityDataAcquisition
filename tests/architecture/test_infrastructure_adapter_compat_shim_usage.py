"""Guardrails for infrastructure adapter compatibility shims."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TESTS_ROOT = ROOT / "tests"
COMPAT_MODULES = frozenset(
    {
        "bioetl.infrastructure.adapters._error_classifier",
        "bioetl.infrastructure.adapters.chembl.fetch_mixin",
        "bioetl.infrastructure.adapters.openalex.client_helpers_mixin",
        "bioetl.infrastructure.adapters.uniprot.metadata_mixin",
    }
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.infrastructure.adapters": frozenset({"_error_classifier"}),
    "bioetl.infrastructure.adapters.chembl": frozenset({"fetch_mixin"}),
    "bioetl.infrastructure.adapters.openalex": frozenset({"client_helpers_mixin"}),
    "bioetl.infrastructure.adapters.uniprot": frozenset({"metadata_mixin"}),
}
ALLOWED_TEST_FILES = frozenset(
    {
        ROOT / "tests" / "architecture" / "test_adapter_contracts.py",
        ROOT
        / "tests"
        / "unit"
        / "infrastructure"
        / "adapters"
        / "test_adapter_error_classifier_compat.py",
        ROOT
        / "tests"
        / "unit"
        / "infrastructure"
        / "adapters"
        / "chembl"
        / "test_fetch_mixin.py",
        ROOT
        / "tests"
        / "unit"
        / "infrastructure"
        / "adapters"
        / "openalex"
        / "test_client_helpers_mixin.py",
        ROOT
        / "tests"
        / "unit"
        / "infrastructure"
        / "adapters"
        / "uniprot"
        / "test_metadata_mixin.py",
    }
)


def _iter_compat_import_violations(
    search_root: Path,
    *,
    allowed_files: frozenset[Path],
) -> list[str]:
    violations: list[str] = []
    for py_file in search_root.rglob("*.py"):
        if py_file in allowed_files or "__pycache__" in py_file.parts:
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
def test_infrastructure_adapter_compat_shims_are_not_used_in_src() -> None:
    """First-party src must import canonical adapter helpers directly."""
    violations = _iter_compat_import_violations(
        SRC_ROOT,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Infrastructure adapter compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_infrastructure_adapter_compat_shims_are_only_used_by_dedicated_tests() -> (
    None
):
    """Ordinary tests must not accumulate new direct imports of adapter shims."""
    violations = _iter_compat_import_violations(
        TESTS_ROOT,
        allowed_files=ALLOWED_TEST_FILES,
    )
    assert not violations, (
        "Infrastructure adapter compatibility shims gained new direct test imports:\n"
        + "\n".join(violations)
    )
