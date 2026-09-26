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
"""Unit tests for composite bootstrap registry manifest."""

from __future__ import annotations

import importlib

import pytest

from bioetl.composition.bootstrap.runtime.composite_bootstrap_registry_manifest import (
    COMPOSITE_BOOTSTRAP_BUILDER_MODULES,
    COMPOSITE_BOOTSTRAP_BUNDLE_MODULES,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("module_path", COMPOSITE_BOOTSTRAP_BUILDER_MODULES.values())
def test_composite_bootstrap_builder_modules_are_importable(module_path: str) -> None:
    module = importlib.import_module(module_path)
    assert module.__name__ == module_path


@pytest.mark.parametrize("module_path", COMPOSITE_BOOTSTRAP_BUNDLE_MODULES.values())
def test_composite_bootstrap_bundle_modules_are_importable(module_path: str) -> None:
    module = importlib.import_module(module_path)
    assert module.__name__ == module_path
