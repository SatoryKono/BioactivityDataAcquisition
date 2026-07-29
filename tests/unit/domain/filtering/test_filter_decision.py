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
"""Unit tests for structured filter decisions."""

from __future__ import annotations

import pytest

from bioetl.domain.filtering import FilterDecision


@pytest.mark.unit
def test_rejected_decision_exposes_stable_analytics_fields() -> None:
    """Structured analytics fields should stay separate from display text."""
    decision = FilterDecision.rejected(
        reason_code="range_filter_mismatch",
        rule_type="range_filters",
        field="pchembl_value",
        operator="range",
        expected={"min_value": 5.0, "max_value": 9.0},
        actual=4.2,
        message="Field 'pchembl_value' failed numeric range filter",
    )

    assert decision.analytics_details() == {
        "reason_code": "range_filter_mismatch",
        "rule_type": "range_filters",
        "field": "pchembl_value",
        "operator": "range",
        "expected": {"min_value": 5.0, "max_value": 9.0},
        "actual": 4.2,
    }
    assert (
        decision.analytics_key()
        == "range_filter_mismatch | range_filters | pchembl_value | range"
    )
    assert decision.to_dict()["message"] == (
        "Field 'pchembl_value' failed numeric range filter"
    )


@pytest.mark.unit
def test_allowed_decision_has_no_analytics_key() -> None:
    """Allow decisions should not produce an analytical rejection key."""
    decision = FilterDecision.allowed()

    assert decision.analytics_key() is None
