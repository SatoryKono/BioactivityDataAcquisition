# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for the runtime builder registry manifest assembly seam."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bioetl.composition.runtime_builders import __all__ as runtime_builder_exports
from bioetl.composition.runtime_builders.registry_manifest import (
    PUBLIC_LAZY_EXPORTS,
    RUNTIME_BUILDER_EXPORTS,
    RuntimeBuilderExportEntry,
)


@pytest.mark.unit
def test_runtime_builder_registry_manifest_matches_lazy_exports() -> None:
    """Manifest entries should mirror the package-level lazy export surface."""
    assert set(runtime_builder_exports) == set(PUBLIC_LAZY_EXPORTS)
    assert tuple(runtime_builder_exports) == tuple(
        entry.export_name for entry in RUNTIME_BUILDER_EXPORTS
    )
    for entry in RUNTIME_BUILDER_EXPORTS:
        assert isinstance(entry, RuntimeBuilderExportEntry)
        assert PUBLIC_LAZY_EXPORTS[entry.export_name] == (
            entry.builder_module,
            entry.target_attr,
        )


@pytest.mark.unit
def test_runtime_builder_registry_manifest_has_no_runtime_calls_or_local_builders() -> (
    None
):
    """The manifest should only declare export ownership without local wiring."""
    source = Path(
        "src/bioetl/composition/runtime_builders/registry_manifest.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)

    called_functions = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called_functions <= {"tuple", "RuntimeBuilderExportEntry"}, (
        "registry_manifest.py should not construct or load builders at runtime:\n"
        + "\n".join(sorted(called_functions))
    )

    local_defs = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert not local_defs, (
        "registry_manifest.py should not define local logic:\n"
        + "\n".join(sorted(local_defs))
    )
