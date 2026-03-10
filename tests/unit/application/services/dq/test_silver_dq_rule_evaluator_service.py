"""Unit tests for DQRuleEvaluatorService."""

from __future__ import annotations

import polars as pl

from bioetl.application.services.dq.silver_dq_rule_evaluator_service import (
    DQRuleEvaluatorService,
)
from bioetl.domain.value_objects.dq_report import DQCheckStatus, DriftLevel


def test_check_record_count_warn_high_quarantine_rate() -> None:
    service = DQRuleEvaluatorService()
    df = pl.DataFrame({"id": [1, 2, 3, 4, 5, 6, 7, 8, 9]})

    result = service.check_record_count(df, 10, 2)

    assert result.status == DQCheckStatus.WARN
    assert result.quarantined_records == 2


def test_check_null_rates_warn_on_high_null_column() -> None:
    service = DQRuleEvaluatorService()
    df = pl.DataFrame({"a": [1, None, None]})

    results, _overall = service.check_null_rates(df)

    assert results[0].status == DQCheckStatus.WARN


def test_check_uniqueness_warn_when_pk_missing() -> None:
    service = DQRuleEvaluatorService()
    df = pl.DataFrame({"id": [1, 2, 3]})

    result = service.check_uniqueness(df, ["missing"])

    assert result.status == DQCheckStatus.WARN


def test_check_type_conformance_warn_on_object_dtype() -> None:
    service = DQRuleEvaluatorService()
    df = pl.DataFrame({"mixed": pl.Series([1, "str"], dtype=pl.Object)})

    result = service.check_type_conformance(df)

    assert result.status == DQCheckStatus.WARN


def test_check_schema_drift_critical_on_missing_field() -> None:
    service = DQRuleEvaluatorService()
    df = pl.DataFrame({"id": [1]})

    result = service.check_schema_drift(df, {"id": "Int64", "name": "String"})

    assert result.drift_level == DriftLevel.CRITICAL
    assert result.status == DQCheckStatus.WARN


def test_check_deduplication_counts_content_hash_duplicates() -> None:
    service = DQRuleEvaluatorService()
    df = pl.DataFrame({"id": [1, 2, 3], "_content_hash": ["h1", "h1", "h3"]})

    result = service.check_deduplication(df, ["id"], 3)

    assert result.duplicates_by_content_hash == 1


def test_check_content_hash_integrity_warn_on_collisions() -> None:
    service = DQRuleEvaluatorService()
    df = pl.DataFrame({"_content_hash": ["h1", "h1", "h2"]})

    result = service.check_content_hash_integrity(df)

    assert result.status == DQCheckStatus.WARN


def test_check_key_nullability_fail_on_non_nullable_violation() -> None:
    service = DQRuleEvaluatorService()
    df = pl.DataFrame({"merge_key": [1, None, 3]})

    result = service.check_key_nullability(
        df,
        [{"field": "merge_key", "key_type": "merge", "nullable": False}],
    )

    assert result["status"] == DQCheckStatus.FAIL.value
    assert result["violations"]
