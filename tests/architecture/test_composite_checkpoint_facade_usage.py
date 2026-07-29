# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Guardrails for the composite checkpoint public facade."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from tests.helpers.compat_shim_guards import (
    find_lingering_files,
    iter_compat_import_violations,
)

ROOT = Path(__file__).resolve().parents[2]
COMPAT_MODULES = frozenset({"bioetl.application.composite.checkpoint.anchor_context"})
REMOVED_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "composite"
        / "checkpoint"
        / "anchor_context.py",
    }
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.application.composite.checkpoint": frozenset({"anchor_context"}),
}


@pytest.mark.architecture
def test_composite_checkpoint_anchor_context_shim_file_stays_removed() -> None:
    """The package root is the only sanctioned public checkpoint facade."""
    lingering = find_lingering_files(root=ROOT, removed_files=REMOVED_FILES)
    assert not lingering, (
        "composite checkpoint anchor-context shim must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_composite_checkpoint_anchor_context_shim_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import checkpoint helpers from the package root."""
    violations = iter_compat_import_violations(
        ast_cache=source_ast_cache,
        root=ROOT,
        compat_modules=COMPAT_MODULES,
        compat_parent_imports=COMPAT_PARENT_IMPORTS,
    )
    assert not violations, (
        "composite checkpoint anchor-context shim is still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_composite_checkpoint_anchor_context_shim_is_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must exercise the package-root checkpoint facade."""
    violations = iter_compat_import_violations(
        ast_cache=test_ast_cache,
        root=ROOT,
        compat_modules=COMPAT_MODULES,
        compat_parent_imports=COMPAT_PARENT_IMPORTS,
    )
    assert not violations, (
        "composite checkpoint anchor-context shim must stay removed from tests:\n"
        + "\n".join(violations)
    )
