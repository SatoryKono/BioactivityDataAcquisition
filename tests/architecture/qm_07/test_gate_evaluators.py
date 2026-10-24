import pytest

"""The source-checkout governance facade must expose working evaluators."""

from scripts.engineering.qa.debt_governance_gate_evaluators import (
    build_architecture_quality_scorecard,
    evaluate_debt_scorecard,
    load_debt_scorecard,
)


@pytest.mark.architecture
@pytest.mark.unit
def test_imports_not_none() -> None:
    assert callable(build_architecture_quality_scorecard)
    assert callable(evaluate_debt_scorecard)
    assert callable(load_debt_scorecard)
