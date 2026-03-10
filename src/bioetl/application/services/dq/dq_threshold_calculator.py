"""Silver DQ threshold calculation component."""

from __future__ import annotations

from bioetl.domain.value_objects.dq_report import DQCheckStatus, DQThresholds


class DQThresholdCalculator:
    """Calculate batch-level error rate thresholds for Silver DQ."""

    def calculate_thresholds(
        self,
        *,
        df_len: int,
        input_record_count: int | None,
        quarantined_count: int,
        soft_fail_threshold: float,
        hard_fail_threshold: float,
    ) -> DQThresholds:
        """Calculate DQ thresholds and corresponding threshold status."""
        total_input = input_record_count or df_len + quarantined_count
        error_rate = quarantined_count / total_input if total_input > 0 else 0.0

        if error_rate >= hard_fail_threshold:
            threshold_status = DQCheckStatus.FAIL
        elif error_rate >= soft_fail_threshold:
            threshold_status = DQCheckStatus.WARN
        else:
            threshold_status = DQCheckStatus.PASS

        return DQThresholds(
            soft_fail_threshold=soft_fail_threshold,
            hard_fail_threshold=hard_fail_threshold,
            current_error_rate=round(error_rate, 4),
            threshold_status=threshold_status,
        )


__all__ = ["DQThresholdCalculator"]
