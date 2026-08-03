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
"""Unit tests for storage write resilience policy builders."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.storage.delta.resilience import (
    build_default_silver_merge_policy,
)

pytestmark = pytest.mark.unit


def test_build_default_silver_merge_policy_matches_pipeline_defaults() -> None:
    """Default storage merge policy must stay aligned with PipelineSettings defaults."""
    policy = build_default_silver_merge_policy()

    assert policy.execution_timeout_seconds == pytest.approx(45.0)
    assert policy.commit_retry.enabled is True
    assert policy.commit_retry.max_retries == 3
    assert policy.commit_retry.base_delay_seconds == pytest.approx(0.250)
    assert policy.commit_retry.max_delay_seconds == pytest.approx(2.0)
    assert policy.commit_retry.jitter_seconds == pytest.approx(0.050)
    assert policy.commit_retry.adaptive is True
    assert policy.timeout_retry.enabled is True
    assert policy.timeout_retry.max_retries == 1
    assert policy.timeout_retry.base_delay_seconds == pytest.approx(0.200)
    assert policy.timeout_retry.max_delay_seconds == pytest.approx(2.0)
    assert policy.timeout_retry.jitter_seconds == pytest.approx(0.050)
    assert policy.timeout_retry.adaptive is True
    assert policy.plain_write_process_isolation is False
