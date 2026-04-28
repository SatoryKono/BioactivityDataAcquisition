"""Guardrails for infrastructure adapter compatibility shims."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from tests.helpers.compat_shim_guards import (
    find_lingering_files,
    iter_compat_import_violations,
)

ROOT = Path(__file__).resolve().parents[2]
COMPAT_MODULES = frozenset(
    {
        "bioetl.infrastructure.adapters._error_classifier",
        "bioetl.infrastructure.adapters.chembl.fetch_mixin",
        "bioetl.infrastructure.adapters.openalex.client_helpers_mixin",
        "bioetl.infrastructure.adapters.uniprot.metadata_mixin",
    }
)
REMOVED_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "_error_classifier.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "chembl"
        / "fetch_mixin.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "openalex"
        / "client_helpers_mixin.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "adapters"
        / "uniprot"
        / "metadata_mixin.py",
    }
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.infrastructure.adapters": frozenset({"_error_classifier"}),
    "bioetl.infrastructure.adapters.chembl": frozenset({"fetch_mixin"}),
    "bioetl.infrastructure.adapters.openalex": frozenset({"client_helpers_mixin"}),
    "bioetl.infrastructure.adapters.uniprot": frozenset({"metadata_mixin"}),
}
@pytest.mark.architecture
def test_infrastructure_adapter_compat_shim_files_have_been_removed() -> None:
    """Removed infrastructure adapter shim files should no longer exist."""
    lingering = find_lingering_files(
        root=ROOT,
        removed_files=REMOVED_FILES,
    )
    assert not lingering, (
        "Infrastructure adapter compatibility shims must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_infrastructure_adapter_compat_shims_are_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import canonical adapter helpers directly."""
    violations = iter_compat_import_violations(
        ast_cache=source_ast_cache,
        root=ROOT,
        compat_modules=COMPAT_MODULES,
        compat_parent_imports=COMPAT_PARENT_IMPORTS,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Infrastructure adapter compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_infrastructure_adapter_compat_shims_are_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing removed adapter shim modules."""
    violations = iter_compat_import_violations(
        ast_cache=test_ast_cache,
        root=ROOT,
        compat_modules=COMPAT_MODULES,
        compat_parent_imports=COMPAT_PARENT_IMPORTS,
        allowed_files=frozenset(),
    )
    assert not violations, (
        "Infrastructure adapter compatibility shims must stay removed from tests:\n"
        + "\n".join(violations)
    )
