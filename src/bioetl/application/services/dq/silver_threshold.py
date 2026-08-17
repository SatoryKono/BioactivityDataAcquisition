"""Silver layer DQ threshold checker.

Stateless checker for DQ threshold logic:
- Error rate calculation and severity classification (PASS/WARN/FAIL)
- Key nullability constraint validation

Extracted from SilverDQAnalyzer (RF-010).
"""

from __future__ import annotations

import polars as pl

from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    DQThresholds,
)


class SilverThresholdChecker:
    """Stateless checker for Silver layer DQ thresholds and key constraints."""

    def calculate_thresholds(
        self,
        df_len: int,
        input_record_count: int | None,
        quarantined_count: int,
        soft_fail_threshold: float,
        hard_fail_threshold: float,
    ) -> DQThresholds:
        """Calculate DQ thresholds and error rate status.

        Args:
            df_len: Length of the DataFrame.
            input_record_count: Original record count before transforms.
            quarantined_count: Number of quarantined records.
            soft_fail_threshold: Warning threshold for error rate.
            hard_fail_threshold: Failure threshold for error rate.

        Returns:
            DQThresholds with calculated error rate and status.
        """
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

    def check_key_nullability(
        self,
        df: pl.DataFrame,
        key_nullability_rules: list[
            JsonDict  # Any: DQ check values vary by check type
        ],  # Any: DQ check values vary by check type
    ) -> JsonDict:  # Any: DQ check values vary by check type
        """Check nullability for configured merge/partition keys.

        Args:
            df: Input Polars DataFrame to check key column null counts on.
            key_nullability_rules: List of rule dicts with 'field', 'key_type',
                and 'nullable' keys. Rules with nullable=True are skipped.

        Returns:
            Dict with 'status' (PASS or FAIL), 'violations' list, and
            'rules_checked' count.
        """
        violations: list[JsonDict] = []  # Any: DQ check values vary by check type

        for rule in key_nullability_rules:
            if rule.get("nullable", False):
                continue
            field = str(rule.get("field", ""))
            key_type = str(rule.get("key_type", "merge"))
            if field not in df.columns:
                violations.append(
                    {
                        "field": field,
                        "key_type": key_type,
                        "missing_column": True,
                    }
                )
                continue
            null_count = int(df[field].null_count())
            if null_count > 0:
                violations.append(
                    {
                        "field": field,
                        "key_type": key_type,
                        "null_count": null_count,
                    }
                )

        status = DQCheckStatus.FAIL if violations else DQCheckStatus.PASS
        return {
            "status": status.value,
            "violations": violations,
            "rules_checked": len(key_nullability_rules),
        }


__all__ = ["SilverThresholdChecker"]
