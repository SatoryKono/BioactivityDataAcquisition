"""Unit tests for SilverDQReportAssemblerService."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.application.services.dq.silver_dq_report_assembler_service import (
    SilverDQReportAssemblerService,
)
from bioetl.domain.value_objects.dq_report import DQCheckStatus, MedallionLayer


def test_calculate_thresholds_warn_status() -> None:
    service = SilverDQReportAssemblerService()

    result = service.calculate_thresholds(
        df_len=95,
        input_record_count=100,
        quarantined_count=10,
        soft_fail_threshold=0.05,
        hard_fail_threshold=0.20,
    )

    assert result.threshold_status == DQCheckStatus.WARN
    assert result.current_error_rate == 0.1


def test_assemble_report_sets_summary_and_layer() -> None:
    service = SilverDQReportAssemblerService()
    thresholds = service.calculate_thresholds(10, 10, 0, 0.05, 0.2)

    report = service.assemble_report(
        run_id="run-1",
        pipeline="chembl",
        target_table="silver/chembl",
        source_batch_ids=["batch-1"],
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        checks={"record_count": {"status": "pass"}},
        thresholds=thresholds,
        passed=1,
        failed=0,
        warnings=0,
    )

    assert report.layer == MedallionLayer.SILVER
    assert report.summary.passed == 1
