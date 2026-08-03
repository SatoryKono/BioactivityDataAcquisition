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
"""Unit tests for the composite runtime compatibility facades."""

from __future__ import annotations

import pytest

from bioetl.application.composite.runtime_models import (
    CompositeRunnerDependencies,
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)
from bioetl.application.composite.runner_pkg import (
    CompositeRunnerDependencies as RunnerPkgCompositeRunnerDependencies,
    CompositeRuntimeConfig as RunnerPkgCompositeRuntimeConfig,
)


pytestmark = pytest.mark.unit


def test_runner_pkg_facade_reexports_runtime_models() -> None:
    """Legacy runner_pkg facade should preserve canonical runtime model identity."""
    assert CompositeRuntimeConfig is RunnerPkgCompositeRuntimeConfig
    assert CompositeRunnerDependencies is RunnerPkgCompositeRunnerDependencies


def test_runtime_models_exports_execution_context_directly() -> None:
    """Execution context remains available from the stable runtime facade."""
    assert CompositeExecutionContext.__name__ == "CompositeExecutionContext"
