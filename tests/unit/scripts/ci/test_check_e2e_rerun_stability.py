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
"""Unit tests for E2E rerun stability classification."""

from __future__ import annotations

import pytest

from scripts.engineering.ci.check_e2e_rerun_stability import (
    CaseOutcome,
    _recurrent_cases,
)

pytestmark = pytest.mark.unit


def test_recurrent_cases_flags_any_non_pass_across_required_runs() -> None:
    run_outcomes = [
        {"case": CaseOutcome("passed", "passed")},
        {"case": CaseOutcome("failed", "code_regression")},
        {"case": CaseOutcome("passed", "passed")},
    ]
    counters, cases = _recurrent_cases(run_outcomes)
    assert cases == [("case", "code_regression")]
    assert counters["code_regression"] == 1


def test_recurrent_cases_pass_all_is_stable() -> None:
    run_outcomes = [
        {"case": CaseOutcome("passed", "passed")},
        {"case": CaseOutcome("passed", "passed")},
        {"case": CaseOutcome("passed", "passed")},
    ]
    counters, cases = _recurrent_cases(run_outcomes)
    assert cases == []
    assert not counters
