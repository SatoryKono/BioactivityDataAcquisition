"""Guardrails for removed pipeline/storage compatibility-only facade imports."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from tests.helpers.compat_shim_guards import (
    find_lingering_files,
    iter_compat_import_violations,
)

ROOT = Path(__file__).resolve().parents[2]
REMOVED_PIPELINE_STORAGE_COMPAT_MODULES = frozenset(
    {
        "bioetl.composition.factories.pipeline.facade",
        "bioetl.composition.factories.storage.facade",
        "bioetl.infrastructure.storage.delta_writer",
        "bioetl.infrastructure.storage.silver_writer_runtime_helpers",
    }
)
REMOVED_PIPELINE_STORAGE_PARENT_IMPORTS = {
    "bioetl.composition.factories.pipeline": frozenset({"facade"}),
    "bioetl.composition.factories.storage": frozenset({"facade"}),
    "bioetl.infrastructure.storage": frozenset(
        {"delta_writer", "silver_writer_runtime_helpers"}
    ),
}
REMOVED_PIPELINE_STORAGE_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "factories"
        / "pipeline"
        / "facade.py",
        ROOT / "src" / "bioetl" / "composition" / "factories" / "storage" / "facade.py",
        ROOT / "src" / "bioetl" / "infrastructure" / "storage" / "delta_writer.py",
        ROOT
        / "src"
        / "bioetl"
        / "infrastructure"
        / "storage"
        / "silver_writer_runtime_helpers.py",
    }
)


@pytest.mark.architecture
def test_removed_pipeline_storage_compat_files_have_been_removed() -> None:
    """Removed pipeline/storage compatibility shims should no longer exist."""
    lingering = find_lingering_files(
        root=ROOT,
        removed_files=REMOVED_PIPELINE_STORAGE_FILES,
    )
    assert not lingering, (
        "Removed pipeline/storage compatibility wrappers must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_removed_pipeline_storage_compat_shims_are_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party source code must use canonical pipeline/storage modules directly."""
    violations = iter_compat_import_violations(
        ast_cache=source_ast_cache,
        root=ROOT,
        compat_modules=REMOVED_PIPELINE_STORAGE_COMPAT_MODULES,
        compat_parent_imports=REMOVED_PIPELINE_STORAGE_PARENT_IMPORTS,
    )
    assert not violations, (
        "Removed pipeline/storage compatibility shims are still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_removed_pipeline_storage_compat_shims_are_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing removed pipeline/storage compatibility modules."""
    violations = iter_compat_import_violations(
        ast_cache=test_ast_cache,
        root=ROOT,
        compat_modules=REMOVED_PIPELINE_STORAGE_COMPAT_MODULES,
        compat_parent_imports=REMOVED_PIPELINE_STORAGE_PARENT_IMPORTS,
    )
    assert not violations, (
        "Removed pipeline/storage compatibility shims must stay absent from tests:\n"
        + "\n".join(violations)
    )
