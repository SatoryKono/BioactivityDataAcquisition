"""Focused unit tests for silver_threshold helpers."""

from __future__ import annotations

import polars as pl
import pytest

from bioetl.application.services.dq.silver_threshold import SilverThresholdChecker
from bioetl.domain.value_objects.dq_report import DQCheckStatus


@pytest.mark.unit
class TestSilverThresholdChecker:
    """Direct tests for threshold and key-nullability logic."""

    def test_calculate_thresholds_derives_total_input_when_missing(self) -> None:
        checker = SilverThresholdChecker()

        result = checker.calculate_thresholds(
            df_len=90,
            input_record_count=None,
            quarantined_count=10,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.2,
        )

        assert result.current_error_rate == pytest.approx(0.1)
        assert result.threshold_status == DQCheckStatus.WARN

    def test_calculate_thresholds_returns_fail_at_hard_threshold(self) -> None:
        checker = SilverThresholdChecker()

        result = checker.calculate_thresholds(
            df_len=80,
            input_record_count=100,
            quarantined_count=20,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.2,
        )

        assert result.current_error_rate == pytest.approx(0.2)
        assert result.threshold_status == DQCheckStatus.FAIL

    def test_calculate_thresholds_handles_zero_total_input(self) -> None:
        checker = SilverThresholdChecker()

        result = checker.calculate_thresholds(
            df_len=0,
            input_record_count=0,
            quarantined_count=0,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.2,
        )

        assert result.current_error_rate == pytest.approx(0.0)
        assert result.threshold_status == DQCheckStatus.PASS

    def test_check_key_nullability_skips_nullable_and_missing_columns(self) -> None:
        checker = SilverThresholdChecker()
        df = pl.DataFrame({"entity_id": ["e1", None], "value": [1, 2]})

        result = checker.check_key_nullability(
            df,
            [
                {"field": "entity_id", "key_type": "merge", "nullable": False},
                {"field": "partition_date", "key_type": "partition", "nullable": False},
                {"field": "value", "key_type": "merge", "nullable": True},
            ],
        )

        assert result["status"] == DQCheckStatus.FAIL.value
        assert result["rules_checked"] == 3
        assert result["violations"] == [
            {"field": "entity_id", "key_type": "merge", "null_count": 1}
        ]

    def test_check_key_nullability_returns_pass_without_violations(self) -> None:
        checker = SilverThresholdChecker()
        df = pl.DataFrame(
            {"entity_id": ["e1", "e2"], "partition_date": ["2026", "2026"]}
        )

        result = checker.check_key_nullability(
            df,
            [
                {"field": "entity_id", "key_type": "merge", "nullable": False},
                {"field": "partition_date", "key_type": "partition", "nullable": False},
            ],
        )

        assert result["status"] == DQCheckStatus.PASS.value
        assert result["violations"] == []
