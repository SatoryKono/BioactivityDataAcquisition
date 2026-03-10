"""Unit tests for DQReportFormatter."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.application.services.dq.dq_report_formatter import DQReportFormatter
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    DQThresholds,
    NumericDistribution,
    ValueDistributionResult,
)


def test_format_distribution_serializes_numeric() -> None:
    formatter = DQReportFormatter()
    dist = ValueDistributionResult(
        numeric_columns={
            "a": NumericDistribution(min=1.0, max=3.0, mean=2.0, std=1.0, median=2.0)
        },
        categorical_columns={},
        status=DQCheckStatus.PASS,
    )

    output = formatter.format_distribution(dist)
    assert output["status"] == DQCheckStatus.PASS.value
    assert output["numeric_columns"]["a"]["mean"] == 2.0


def test_build_report_creates_silver_report() -> None:
    formatter = DQReportFormatter()
    thresholds = DQThresholds(
        soft_fail_threshold=0.05,
        hard_fail_threshold=0.2,
        current_error_rate=0.0,
        threshold_status=DQCheckStatus.PASS,
    )
    report = formatter.build_report(
        timestamp=datetime.now(UTC),
        run_id="run-1",
        pipeline="p",
        source_batch_ids=["b1"],
        target_table="silver.table",
        checks={},
        thresholds=thresholds,
        passed=1,
        failed=0,
        warnings=0,
    )
    assert report.run_id == "run-1"
    assert report.thresholds.threshold_status == DQCheckStatus.PASS
