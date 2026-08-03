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
"""Tests for dependency-join support aggregate exports."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_dependency_join_support_reexports_canonical_helpers_and_models() -> None:
    """Aggregate dependency-join seam should expose canonical helper owners."""
    support_module = importlib.import_module(
        "bioetl.application.composite.dependency_join_support"
    )
    builders_module = importlib.import_module(
        "bioetl.application.composite.dependency_join_context_builders"
    )
    execution_module = importlib.import_module(
        "bioetl.application.composite.dependency_join_execution"
    )
    models_module = importlib.import_module(
        "bioetl.application.composite.dependency_join_models"
    )

    assert support_module.build_prepared_dependency_join_context is (
        builders_module.build_prepared_dependency_join_context
    )
    assert support_module.prepare_dependency_join_frames is (
        builders_module.prepare_dependency_join_frames
    )
    assert support_module.execute_dependency_join is (
        execution_module.execute_dependency_join
    )
    assert support_module.resolve_single_key_join_context is (
        execution_module.resolve_single_key_join_context
    )
    assert support_module.CompositeJoinContext is models_module.CompositeJoinContext
    assert (
        support_module.PreparedDependencyJoinContext
        is models_module.PreparedDependencyJoinContext
    )
