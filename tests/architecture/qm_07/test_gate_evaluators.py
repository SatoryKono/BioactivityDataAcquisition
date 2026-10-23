import pytest

pytestmark = pytest.mark.unit
from scripts.engineering.qa.debt_governance_gate_evaluators import (
    build_architecture_quality_scorecard,
    evaluate_debt_scorecard,
    load_debt_scorecard,
)


def test_imports_not_none():
    assert build_architecture_quality_scorecard is not None
    assert evaluate_debt_scorecard is not None
    assert load_debt_scorecard is not None
