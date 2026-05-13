"""Guardrails for the checkpoint compatibility runtime facade."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from tests.helpers.compat_shim_guards import iter_compat_import_violations

ROOT = Path(__file__).resolve().parents[2]
COMPAT_MODULES = frozenset(
    {"bioetl.application.services.checkpoint_compatibility_runtime"}
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.application.services": frozenset({"checkpoint_compatibility_runtime"}),
}


@pytest.mark.architecture
def test_checkpoint_compatibility_runtime_facade_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import checkpoint compatibility owners directly."""
    violations = iter_compat_import_violations(
        ast_cache=source_ast_cache,
        root=ROOT,
        compat_modules=COMPAT_MODULES,
        compat_parent_imports=COMPAT_PARENT_IMPORTS,
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
        compat_modules=COMPAT_MODULES,
        compat_parent_imports=COMPAT_PARENT_IMPORTS,
    )
    assert not violations, (
        "checkpoint_compatibility_runtime facade must stay absent from tests:\n"
        + "\n".join(violations)
    )
