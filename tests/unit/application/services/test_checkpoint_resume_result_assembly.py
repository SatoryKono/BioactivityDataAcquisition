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
"""Unit tests for checkpoint resume result assembly helpers."""

from __future__ import annotations

import pytest

from bioetl.application.services.checkpoint.checkpoint_compatibility_results import (
    build_lenient_checkpoint_compatibility_result,
    build_strict_checkpoint_compatibility_result,
)


@pytest.mark.unit
def test_strict_checkpoint_result_gates_identity_on_required_anchors() -> None:
    """Strict result assembly must preserve required-anchor replay safety."""
    result = build_strict_checkpoint_compatibility_result(
        compatible=False,
        dq_compatible=True,
        pipeline_compatible=True,
        execution_identity_compatible=True,
        identity_continuity_proven=True,
        required_anchor_compatible=False,
        messages=("missing execution fingerprint",),
    )

    assert result.compatible is False
    assert result.dq_compatible is True
    assert result.pipeline_compatible is True
    assert result.execution_identity_compatible is False
    assert result.identity_continuity_proven is False
    assert result.messages == ("missing execution fingerprint",)


@pytest.mark.unit
def test_lenient_checkpoint_result_reports_degraded_resume_verdict() -> None:
    """Lenient result assembly must expose degraded resume reasons."""
    result = build_lenient_checkpoint_compatibility_result(
        compatible=True,
        dq_compatible=True,
        pipeline_compatible=True,
        execution_identity_compatible=True,
        identity_continuity_proven=True,
        messages=("compatible", "config drift accepted"),
        degraded_messages=("config drift accepted",),
    )

    assert result.compatible is True
    assert result.resume_verdict == "resume_only_degraded"
    assert result.degraded_resume_reasons == ("config drift accepted",)
    assert result.messages == ("compatible", "config drift accepted")
