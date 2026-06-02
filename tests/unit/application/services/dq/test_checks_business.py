"""Direct unit tests for the ``_checks_business`` Gold DQ helpers."""

from __future__ import annotations

import polars as pl
import pytest

from bioetl.application.services.dq import _checks_business
from bioetl.application.services.dq._checks_business import check_business_rules
from bioetl.domain.value_objects.dq_report import DQCheckStatus


pytestmark = pytest.mark.unit


class TestCheckBusinessRulesDirect:
    """Direct ownership tests for ``check_business_rules``."""

    def test_in_list_rule_with_empty_allowed_values_passes(self) -> None:
        df = pl.DataFrame({"category": ["A", "B", "C"]})

        result = check_business_rules(
            df,
            [
                {
                    "rule_id": "R-EMPTY-LIST",
                    "column": "category",
                    "condition": "in_list",
                    "values": [],
                }
            ],
        )

        assert result.status == DQCheckStatus.PASS
        assert result.rules_passed == 1
        assert result.rules[0].violations == 0

    def test_regex_rule_with_empty_pattern_passes(self) -> None:
        df = pl.DataFrame({"code": ["AA-1", "BB-2"]})

        result = check_business_rules(
            df,
            [
                {
                    "rule_id": "R-EMPTY-REGEX",
                    "column": "code",
                    "condition": "regex",
                    "pattern": "",
                }
            ],
        )

        assert result.status == DQCheckStatus.PASS
        assert result.rules_passed == 1
        assert result.rules[0].violations == 0

    def test_missing_column_is_treated_as_skipped_pass(self) -> None:
        df = pl.DataFrame({"present": [1, 2, 3]})

        result = check_business_rules(
            df,
            [
                {
                    "rule_id": "R-MISSING-COL",
                    "name": "Missing column rule",
                    "column": "missing",
                    "condition": "not_null",
                    "field": "business_key",
                    "decision": "warn",
                }
            ],
        )

        assert result.status == DQCheckStatus.PASS
        assert result.rules[0].passed is True
        assert result.rules[0].violations == 0
        assert result.rules[0].field == "business_key"
        assert result.rules[0].decision == "warn"

    def test_rule_evaluation_error_is_reported_as_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        df = pl.DataFrame({"value": [1, 2, 3]})

        def _raise_value_error(
            _df: pl.DataFrame,
            _rule: object,
        ) -> tuple[bool, int | None]:
            raise ValueError("synthetic evaluation failure")

        monkeypatch.setattr(
            _checks_business, "_evaluate_single_rule", _raise_value_error
        )

        result = check_business_rules(
            df,
            [
                {
                    "rule_id": "R-ERROR",
                    "column": "value",
                    "condition": "range",
                    "min": 0,
                    "max": 10,
                }
            ],
        )

        assert result.status == DQCheckStatus.FAIL
        assert result.rules_failed == 1
        assert result.rules[0].passed is False
        assert result.rules[0].violations is None
        assert result.rules[0].decision == "fail"
