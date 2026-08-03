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
"""Tests for composition/bootstrap_contexts.py module exports."""

from __future__ import annotations


import pytest

pytestmark = pytest.mark.unit


class TestBootstrapContextsModuleExports:
    """Tests for bootstrap context naming and module exports."""

    def test_rate_limit_context_importable(self) -> None:
        """RateLimitContext is importable from bootstrap_contexts."""
        from bioetl.composition.bootstrap_contexts import RateLimitContext

        assert RateLimitContext.__name__ == "RateLimitContext"

    def test_legacy_rate_limit_config_not_exported(self) -> None:
        """Legacy RateLimitConfig is not exported from bootstrap_contexts."""
        from bioetl.composition import bootstrap_contexts

        assert "RateLimitContext" in bootstrap_contexts.__all__
        assert "RateLimitConfig" not in bootstrap_contexts.__all__
        assert not hasattr(bootstrap_contexts, "RateLimitConfig")
