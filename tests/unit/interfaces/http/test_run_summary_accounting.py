"""Persisted accounting cannot invent counts or a denominator."""

import pytest

from bioetl.interfaces.http._run_summary_accounting import summary_accounting

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("invalid", [None, True, -1, "10", 2.5])
def test_invalid_count_is_unknown(invalid):
    result = summary_accounting({"layers": {"silver_valid": invalid}})
    assert result["silver_valid"] is None
    assert result["contract_excluded_percent"] is None


def test_exclusions_use_accepted_not_input_as_denominator():
    result = summary_accounting(
        {
            "layers": {
                "bronze_records": 200,
                "silver_valid": 100,
                "gold_excluded_by_contract": 20,
                "gold_written": 80,
            }
        }
    )
    assert result["contract_excluded_percent"] == 20
    assert result["silver_quarantined"] is None
    assert result["gold_written"] == 80


@pytest.mark.parametrize(
    "layers", [None, [], {}, {"silver_valid": 0, "gold_excluded_by_contract": 0}]
)
def test_no_denominator_does_not_claim_zero_percent(layers):
    assert summary_accounting({"layers": layers})["contract_excluded_percent"] is None
