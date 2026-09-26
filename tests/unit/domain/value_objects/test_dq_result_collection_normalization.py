"""Collection normalization contract for immutable DQ results."""

from __future__ import annotations

from typing import Any, cast

import pytest

from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQRuleOutcome,
    DQViolationKind,
)
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult

pytestmark = pytest.mark.unit


def test_rule_outcome_list_is_frozen_as_tuple() -> None:
    """Compatibility list input cannot leave a mutable collection in DQResult."""
    outcome = DQRuleOutcome(
        rule_id="schema.required",
        violation_kind=DQViolationKind.SCHEMA_VIOLATION,
        severity="high",
        disposition=DQDisposition.FAIL,
    )

    result = DQResult(
        error_rate=1.0,
        status=DQEvaluationStatus.FAILED,
        rule_outcomes=cast(Any, [outcome]),
    )

    assert result.rule_outcomes == (outcome,)
