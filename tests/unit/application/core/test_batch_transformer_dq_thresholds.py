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
"""Unit tests for batch transformer DQ threshold helpers (#7836)."""

from __future__ import annotations

import pytest

from bioetl.application.core.batch_transformer_dq_thresholds import (
    ThresholdBreachReason,
    check_dq_thresholds,
    classify_dq_threshold_breach,
    compute_error_rate,
    resolve_threshold_value,
)


@pytest.mark.unit
def test_check_dq_thresholds_zero_records() -> None:
    result = check_dq_thresholds(
        error_count=5,
        record_count=0,
        soft_threshold=0.05,
        hard_threshold=0.2,
    )
    assert result.breach is ThresholdBreachReason.NONE
    assert result.error_rate == 0.0


@pytest.mark.unit
def test_check_dq_thresholds_nominal_below_soft() -> None:
    result = check_dq_thresholds(
        error_count=1,
        record_count=100,
        soft_threshold=0.05,
        hard_threshold=0.2,
    )
    assert result.breach is ThresholdBreachReason.NONE
    assert result.error_rate == pytest.approx(0.01)


@pytest.mark.unit
def test_check_dq_thresholds_soft_boundary_inclusive() -> None:
    result = check_dq_thresholds(
        error_count=5,
        record_count=100,
        soft_threshold=0.05,
        hard_threshold=0.2,
    )
    assert result.breach is ThresholdBreachReason.SOFT
    assert result.error_rate == pytest.approx(0.05)


@pytest.mark.unit
def test_check_dq_thresholds_hard_boundary_inclusive() -> None:
    result = check_dq_thresholds(
        error_count=20,
        record_count=100,
        soft_threshold=0.05,
        hard_threshold=0.2,
    )
    assert result.breach is ThresholdBreachReason.HARD
    assert result.error_rate == pytest.approx(0.2)


@pytest.mark.unit
def test_check_dq_thresholds_hard_precedence_when_both_breached() -> None:
    result = check_dq_thresholds(
        error_count=50,
        record_count=100,
        soft_threshold=0.05,
        hard_threshold=0.2,
    )
    assert result.breach is ThresholdBreachReason.HARD


@pytest.mark.unit
def test_classify_and_compute_helpers() -> None:
    assert compute_error_rate(0, 0) == 0.0
    assert compute_error_rate(1, 4) == pytest.approx(0.25)
    assert (
        classify_dq_threshold_breach(0.05, soft_threshold=0.05, hard_threshold=0.2)
        is ThresholdBreachReason.SOFT
    )
    assert (
        classify_dq_threshold_breach(0.2, soft_threshold=0.05, hard_threshold=0.2)
        is ThresholdBreachReason.HARD
    )


@pytest.mark.unit
def test_resolve_threshold_value_ignores_bool_and_missing() -> None:
    class _Cfg:
        soft = 0.1
        flag = True

    assert resolve_threshold_value(_Cfg(), "soft") == 0.1
    assert resolve_threshold_value(_Cfg(), "flag") is None
    assert resolve_threshold_value(None, "soft") is None
    assert resolve_threshold_value(_Cfg(), "missing", "soft") == 0.1
