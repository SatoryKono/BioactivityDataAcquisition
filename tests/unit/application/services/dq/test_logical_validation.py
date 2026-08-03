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
"""Logical DQ validation tests against real check/analyzer outputs.

These tests intentionally avoid self-fulfilling assertions and validate
actual outputs from:
- check_business_rules
- GoldDQAnalyzer
- SilverDQAnalyzer
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.services.dq._checks_business import check_business_rules
from bioetl.application.services.dq.gold_analyzer import GoldDQAnalyzer
from bioetl.application.services.dq.silver_check_executor import SilverCheckExecutor
from bioetl.application.services.dq.silver_analyzer import SilverDQAnalyzer
from bioetl.application.services.dq.silver_statistics import SilverStatisticsCalculator
from bioetl.application.services.dq.silver_threshold import SilverThresholdChecker
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    GoldDQCheckType,
    SilverDQCheckType,
)


def _derive_row_dq_flags(
    *,
    failed_rules: list[dict[str, str]],
) -> dict[str, str | bool]:
    """Map failed rule severities to record-level DQ flags for assertions."""
    error_reasons = [r["reason"] for r in failed_rules if r["severity"] == "error"]
    warn_reasons = [r["reason"] for r in failed_rules if r["severity"] == "warn"]

    if error_reasons:
        severity = "error"
    elif warn_reasons:
        severity = "warn"
    else:
        severity = "pass"

    reason = " | ".join(error_reasons or warn_reasons)

    return {
        "_dq_error": bool(error_reasons),
        "_dq_warn": bool(warn_reasons) and not bool(error_reasons),
        "severity": severity,
        "reason": reason,
    }


def _build_silver_analyzer() -> SilverDQAnalyzer:
    statistics = SilverStatisticsCalculator()
    threshold_checker = SilverThresholdChecker()
    return SilverDQAnalyzer(
        statistics=statistics,
        threshold_checker=threshold_checker,
        check_executor=SilverCheckExecutor(
            statistics=statistics,
            threshold_checker=threshold_checker,
        ),
    )


@pytest.fixture()
def logical_rules() -> list[dict[str, object]]:
    """Representative logical rules with mixed severities."""
    return [
        {
            "rule_id": "pub_year_min",
            "name": "publication_year_min",
            "description": "publication_year must be >= 1500",
            "column": "publication_year",
            "condition": "range",
            "min": 1500,
            "severity": "error",
            "decision": "fail",
        },
        {
            "rule_id": "pub_year_max",
            "name": "publication_year_max",
            "description": "publication_year > 2100 is suspicious",
            "column": "publication_year",
            "condition": "range",
            "max": 2100,
            "severity": "warn",
            "decision": "warn",
        },
        {
            "rule_id": "cit_non_negative",
            "name": "citations_non_negative",
            "description": "citations_received must be >= 0",
            "column": "citations_received",
            "condition": "range",
            "min": 0,
            "severity": "error",
            "decision": "fail",
        },
    ]


@pytest.mark.unit
class TestLogicalBusinessChecks:
    """Logical validations must assert checker outputs, not hand-written conditions."""

    def test_logical_rules_pass_without_flags(
        self, logical_rules: list[dict[str, object]]
    ) -> None:
        df = pl.DataFrame(
            {
                "publication_year": [2024],
                "citations_received": [10],
            }
        )

        result = check_business_rules(df, logical_rules)
        failed_rules = [
            {
                "severity": str(rule.severity or "error"),
                "reason": str(rule.description or rule.name or rule.rule_id),
            }
            for rule in result.rules
            if not rule.passed
        ]
        flags = _derive_row_dq_flags(failed_rules=failed_rules)

        assert result.status == DQCheckStatus.PASS
        assert flags["_dq_error"] is False
        assert flags["_dq_warn"] is False
        assert flags["severity"] == "pass"
        assert flags["reason"] == ""

    def test_negative_citations_sets_dq_error_and_reason(
        self, logical_rules: list[dict[str, object]]
    ) -> None:
        df = pl.DataFrame(
            {
                "publication_year": [2024],
                "citations_received": [-1],
            }
        )

        result = check_business_rules(df, logical_rules)
        failed_rules = [
            {
                "severity": str(rule.severity or "error"),
                "reason": str(rule.description or rule.name or rule.rule_id),
            }
            for rule in result.rules
            if not rule.passed
        ]
        flags = _derive_row_dq_flags(failed_rules=failed_rules)

        assert result.status == DQCheckStatus.FAIL
        assert flags["_dq_error"] is True
        assert flags["_dq_warn"] is False
        assert flags["severity"] == "error"
        assert "citations_received must be >= 0" in str(flags["reason"])

    def test_future_year_sets_dq_warn_without_dq_error(
        self, logical_rules: list[dict[str, object]]
    ) -> None:
        df = pl.DataFrame(
            {
                "publication_year": [2201],
                "citations_received": [10],
            }
        )

        result = check_business_rules(df, logical_rules)
        failed_rules = [
            {
                "severity": str(rule.severity or "error"),
                "reason": str(rule.description or rule.name or rule.rule_id),
            }
            for rule in result.rules
            if not rule.passed
        ]
        flags = _derive_row_dq_flags(failed_rules=failed_rules)

        assert result.status == DQCheckStatus.FAIL
        assert flags["_dq_error"] is False
        assert flags["_dq_warn"] is True
        assert flags["severity"] == "warn"
        assert "publication_year > 2100 is suspicious" in str(flags["reason"])

    def test_negative_citations_and_future_year_reports_error_priority(
        self, logical_rules: list[dict[str, object]]
    ) -> None:
        df = pl.DataFrame(
            {
                "publication_year": [2201],
                "citations_received": [-1],
            }
        )

        result = check_business_rules(df, logical_rules)
        failed_rules = [
            {
                "severity": str(rule.severity or "error"),
                "reason": str(rule.description or rule.name or rule.rule_id),
            }
            for rule in result.rules
            if not rule.passed
        ]
        flags = _derive_row_dq_flags(failed_rules=failed_rules)

        assert result.status == DQCheckStatus.FAIL
        assert flags["_dq_error"] is True
        assert flags["_dq_warn"] is False
        assert flags["severity"] == "error"
        assert "citations_received must be >= 0" in str(flags["reason"])
        assert any(
            rule.description == "publication_year > 2100 is suspicious"
            for rule in result.rules
            if not rule.passed
        )


@pytest.mark.unit
class TestLogicalAnalyzerIntegration:
    """Logical checks should be visible in analyzer reports."""

    def test_gold_analyzer_exposes_rule_severity_and_reason(
        self, logical_rules: list[dict[str, object]]
    ) -> None:
        analyzer = GoldDQAnalyzer()

        config = MagicMock()
        config.get_checks_enums.return_value = [GoldDQCheckType.BUSINESS_RULES]

        report = analyzer.analyze(
            data=pl.DataFrame(
                {
                    "publication_year": [2201],
                    "citations_received": [10],
                }
            ),
            run_id="rf01-logical-gold",
            pipeline="test_pipeline",
            target_table="gold.test",
            config=config,
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            business_rules=logical_rules,
        )

        business_rules_result = report.checks["business_rules"]
        failed = [r for r in business_rules_result["rules"] if not r["passed"]]

        assert business_rules_result["status"] == DQCheckStatus.FAIL.value
        assert failed
        assert failed[0]["severity"] in {"warn", "error"}
        assert isinstance(failed[0]["description"], str)
        assert failed[0]["description"]

    def test_silver_analyzer_threshold_warn_maps_to_dq_warn(self) -> None:
        analyzer = _build_silver_analyzer()

        config = MagicMock()
        config.get_checks_enums.return_value = [SilverDQCheckType.RECORD_COUNT]

        report = analyzer.analyze(
            data=pl.DataFrame({"id": list(range(90))}),
            run_id="rf01-logical-silver",
            pipeline="test_pipeline",
            target_table="silver.test",
            source_batch_ids=["batch-1"],
            config=config,
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            primary_keys=["id"],
            input_record_count=100,
            quarantined_count=10,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )

        threshold_status = report.thresholds.threshold_status
        flags = {
            "_dq_error": threshold_status == DQCheckStatus.FAIL,
            "_dq_warn": threshold_status == DQCheckStatus.WARN,
            "severity": "warn" if threshold_status == DQCheckStatus.WARN else "pass",
            "reason": "error_rate_above_soft_threshold"
            if threshold_status == DQCheckStatus.WARN
            else "",
        }

        assert threshold_status == DQCheckStatus.WARN
        assert flags["_dq_error"] is False
        assert flags["_dq_warn"] is True
        assert flags["severity"] == "warn"
        assert flags["reason"] == "error_rate_above_soft_threshold"

    def test_business_rules_with_missing_column_are_treated_as_pass(self) -> None:
        df = pl.DataFrame({"publication_year": [2024], "citations_received": [10]})
        rules_with_missing_column = [
            {
                "rule_id": "extra_missing",
                "name": "missing_column",
                "description": "column does not exist in dataframe",
                "column": "missing_column",
                "condition": "range",
                "min": 1,
                "severity": "error",
                "decision": "fail",
            }
        ]

        result = check_business_rules(df, rules_with_missing_column)

        assert result.status == DQCheckStatus.PASS
        assert result.rules_evaluated == 1
        assert result.rules_failed == 0
