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
"""Tests for RunOptions execution_context handling."""

from __future__ import annotations

import pytest

from bioetl.application.services.execution.pipeline_runner_models import RunOptions


pytestmark = pytest.mark.unit


class TestRunOptionsSeverityContext:
    """Tests for RunOptions execution_context field."""

    def test_default_execution_context(self) -> None:
        opts = RunOptions()
        assert opts.execution_context == "isolated"

    def test_enricher_execution_context(self) -> None:
        opts = RunOptions(execution_context="enricher")
        assert opts.execution_context == "enricher"

    def test_dependency_execution_context(self) -> None:
        opts = RunOptions(execution_context="dependency")
        assert opts.execution_context == "dependency"
