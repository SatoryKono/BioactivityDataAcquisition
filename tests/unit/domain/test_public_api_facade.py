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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Focused unit tests for the top-level domain lazy facade."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


def test_domain_lazy_module_export_is_cached() -> None:
    """Module exports should resolve once and then stay cached on the facade."""
    import bioetl.domain as domain

    domain.__dict__.pop("workflow", None)

    workflow_module = domain.__getattr__("workflow")

    assert workflow_module.__name__ == "bioetl.domain.workflow"
    assert domain.workflow is workflow_module


def test_domain_lazy_facade_dir_and_unknown_export_are_deterministic() -> None:
    """The facade exposes declared lazy names and rejects implicit compat seams."""
    import bioetl.domain as domain

    exported = dir(domain)

    assert "workflow" in exported
    assert "DomainEventObservabilityEnvelope" in exported
    missing_name = "not_a_domain_export"
    with pytest.raises(AttributeError, match=missing_name):
        getattr(domain, missing_name)
