"""Guardrails for the removed checkpoint compatibility runtime facade."""

from __future__ import annotations

import ast
from importlib import import_module
from pathlib import Path

import pytest
from tests.helpers.compat_shim_guards import (
    find_lingering_files,
    iter_compat_import_violations,
)

ROOT = Path(__file__).resolve().parents[2]
REMOVED_COMPAT_MODULES = frozenset(
    {"bioetl.application.services.checkpoint_compatibility_runtime"}
)
REMOVED_COMPAT_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "checkpoint_compatibility_runtime.py",
    }
)
REMOVED_COMPAT_PARENT_IMPORTS = {
    "bioetl.application.services": frozenset({"checkpoint_compatibility_runtime"}),
}


@pytest.mark.architecture
def test_checkpoint_compatibility_runtime_facade_file_stays_absent() -> None:
    """Removed checkpoint runtime facade file must not return."""
    lingering = find_lingering_files(root=ROOT, removed_files=REMOVED_COMPAT_FILES)
    assert not lingering, (
        "checkpoint_compatibility_runtime facade file must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_checkpoint_compatibility_runtime_facade_import_fails() -> None:
    """Removed checkpoint runtime facade module must stay unimportable."""
    with pytest.raises(ModuleNotFoundError):
        import_module("bioetl.application.services.checkpoint_compatibility_runtime")


@pytest.mark.architecture
def test_checkpoint_compatibility_runtime_facade_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import checkpoint compatibility owners directly."""
    violations = iter_compat_import_violations(
        ast_cache=source_ast_cache,
        root=ROOT,
        compat_modules=REMOVED_COMPAT_MODULES,
        compat_parent_imports=REMOVED_COMPAT_PARENT_IMPORTS,
    )
    assert not violations, (
        "checkpoint_compatibility_runtime facade leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_checkpoint_compatibility_runtime_facade_is_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not reintroduce the checkpoint compatibility runtime facade."""
    violations = iter_compat_import_violations(
        ast_cache=test_ast_cache,
        root=ROOT,
        compat_modules=REMOVED_COMPAT_MODULES,
        compat_parent_imports=REMOVED_COMPAT_PARENT_IMPORTS,
    )
    assert not violations, (
        "checkpoint_compatibility_runtime facade must stay absent from tests:\n"
        + "\n".join(violations)
    )
