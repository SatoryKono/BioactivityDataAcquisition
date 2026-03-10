"""Unit tests for DQThresholdCalculator."""

from __future__ import annotations

from bioetl.application.services.dq.dq_threshold_calculator import DQThresholdCalculator
from bioetl.domain.value_objects.dq_report import DQCheckStatus


class TestDQThresholdCalculator:
    def test_pass_status_no_quarantined(self) -> None:
        calculator = DQThresholdCalculator()
        result = calculator.calculate_thresholds(
            df_len=100,
            input_record_count=100,
            quarantined_count=0,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )
        assert result.threshold_status == DQCheckStatus.PASS
        assert result.current_error_rate == 0.0

    def test_warn_and_fail_thresholds(self) -> None:
        calculator = DQThresholdCalculator()
        warn = calculator.calculate_thresholds(
            df_len=95,
            input_record_count=100,
            quarantined_count=10,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )
        fail = calculator.calculate_thresholds(
            df_len=80,
            input_record_count=100,
            quarantined_count=25,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )
        assert warn.threshold_status == DQCheckStatus.WARN
        assert fail.threshold_status == DQCheckStatus.FAIL

    def test_none_input_count_and_zero_total(self) -> None:
        calculator = DQThresholdCalculator()
        none_input = calculator.calculate_thresholds(
            df_len=90,
            input_record_count=None,
            quarantined_count=10,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )
        zero = calculator.calculate_thresholds(
            df_len=0,
            input_record_count=0,
            quarantined_count=0,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )
        assert none_input.current_error_rate == 0.1
        assert zero.current_error_rate == 0.0
