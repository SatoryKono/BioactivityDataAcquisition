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
"""Smoke coverage for composition bootstrap runtime bundle dataclasses."""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "module_path",
    [
        "bioetl.composition.bootstrap.runtime.observability_bundle",
        "bioetl.composition.bootstrap.runtime.composite_control_plane_bundle",
        "bioetl.composition.bootstrap.runtime.composite_execution_support_bundle",
        "bioetl.composition.bootstrap.runtime.composite_merge_dependencies_bundle",
        "bioetl.composition.bootstrap.runtime.composite_runtime_management_bundle",
    ],
)
def test_runtime_bundle_modules_expose_public_dataclass(module_path: str) -> None:
    """Each runtime bundle module must import and expose a public bundle type."""
    module = importlib.import_module(module_path)
    exported = [name for name in dir(module) if name.endswith("Bundle")]
    assert exported, f"{module_path} must export a *Bundle type"
    bundle_cls = getattr(module, exported[0])
    assert hasattr(bundle_cls, "__annotations__")
