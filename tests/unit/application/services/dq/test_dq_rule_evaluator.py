"""Unit tests for DQRuleEvaluator responsibilities."""

from __future__ import annotations

import polars as pl

from bioetl.application.services.dq.dq_report_formatter import DQReportFormatter
from bioetl.application.services.dq.dq_rule_evaluator import DQRuleEvaluator
from bioetl.domain.value_objects.dq_report import DQCheckStatus, SilverDQCheckType


def test_record_count_and_null_rate_checks() -> None:
    evaluator = DQRuleEvaluator()
    df = pl.DataFrame({"id": [1, 2, 3], "a": [1, None, None]})

    record_count = evaluator.check_record_count(df, 10, 2)
    null_results, overall = evaluator.check_null_rates(df)

    assert record_count.status == DQCheckStatus.WARN
    assert null_results[1].status == DQCheckStatus.WARN
    assert overall > 0.0


def test_uniqueness_type_and_schema_drift_checks() -> None:
    evaluator = DQRuleEvaluator()
    df = pl.DataFrame({"id": [1, 1, 2], "name": ["a", "b", "c"]})

    uniqueness = evaluator.check_uniqueness(df, ["id"])
    conformance = evaluator.check_type_conformance(df)
    drift = evaluator.check_schema_drift(df, {"id": "Int64", "legacy_col": "Utf8"})

    assert uniqueness.status == DQCheckStatus.WARN
    assert conformance.status == DQCheckStatus.PASS
    assert drift.status == DQCheckStatus.WARN


def test_distribution_deduplication_hash_and_key_nullability() -> None:
    evaluator = DQRuleEvaluator()
    formatter = DQReportFormatter()
    df = pl.DataFrame(
        {
            "_content_hash": ["h1", "h1", "h2"],
            "id": [1, 2, 3],
            "category": ["x", "x", "y"],
            "value": [1.0, 2.0, 3.0],
            "merge_key": [1, None, 3],
        }
    )

    distribution = evaluator.check_value_distribution(df)
    serialized = formatter.format_distribution(distribution)
    dedupe = evaluator.check_deduplication(df, ["id"], 5)
    integrity = evaluator.check_content_hash_integrity(df)
    nullability = evaluator.check_key_nullability(
        df, [{"field": "merge_key", "nullable": False, "key_type": "merge"}]
    )

    assert serialized["status"] == DQCheckStatus.PASS.value
    assert dedupe.output_after_dedupe == 3
    assert integrity.status == DQCheckStatus.WARN
    assert nullability["status"] == DQCheckStatus.FAIL.value


def test_evaluate_checks_aggregates_results() -> None:
    evaluator = DQRuleEvaluator()
    df = pl.DataFrame({"id": [1, 2], "_content_hash": ["a", "b"]})

    checks, passed, failed, warnings = evaluator.evaluate_checks(
        df=df,
        enabled_checks={SilverDQCheckType.RECORD_COUNT, SilverDQCheckType.UNIQUENESS},
        primary_keys=["id"],
        input_record_count=2,
        quarantined_count=0,
        previous_schema=None,
        key_nullability_rules=[],
    )

    assert "record_count" in checks
    assert "uniqueness" in checks
    assert passed == 2
    assert failed == 0
    assert warnings == 0
