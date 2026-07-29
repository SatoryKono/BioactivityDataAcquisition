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
"""Guardrails for batch_transformer_helpers compatibility shim."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from tests.helpers.compat_shim_guards import (
    find_lingering_files,
    iter_compat_import_violations,
)

ROOT = Path(__file__).resolve().parents[2]
COMPAT_MODULE = "bioetl.application.core.batch_transformer_helpers"
REMOVED_FILE = (
    ROOT / "src" / "bioetl" / "application" / "core" / "batch_transformer_helpers.py"
)
COMPAT_PARENT_IMPORTS = {
    "bioetl.application.core": frozenset({"batch_transformer_helpers"}),
}


@pytest.mark.architecture
def test_batch_transformer_helpers_shim_file_has_been_removed() -> None:
    """The batch_transformer_helpers compatibility module should no longer exist."""
    lingering = find_lingering_files(root=ROOT, removed_files=(REMOVED_FILE,))
    assert not lingering, (
        "batch_transformer_helpers compatibility shim must stay removed: "
        "src/bioetl/application/core/batch_transformer_helpers.py"
    )


@pytest.mark.architecture
def test_batch_transformer_helpers_shim_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import canonical batch-transform helper modules directly."""
    violations = iter_compat_import_violations(
        ast_cache=source_ast_cache,
        root=ROOT,
        compat_modules=frozenset({COMPAT_MODULE}),
        compat_parent_imports=COMPAT_PARENT_IMPORTS,
    )
    assert not violations, (
        "batch_transformer_helpers compatibility shim is still imported from src/:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_batch_transformer_helpers_shim_is_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing the removed helper shim."""
    violations = iter_compat_import_violations(
        ast_cache=test_ast_cache,
        root=ROOT,
        compat_modules=frozenset({COMPAT_MODULE}),
        compat_parent_imports=COMPAT_PARENT_IMPORTS,
    )
    assert not violations, (
        "batch_transformer_helpers compatibility shim must stay removed from tests:\n"
        + "\n".join(violations)
    )
