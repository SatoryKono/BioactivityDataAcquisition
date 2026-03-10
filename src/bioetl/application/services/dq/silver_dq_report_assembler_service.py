"""Silver DQ report assembler service."""

from __future__ import annotations

from datetime import datetime

from bioetl.application.services.dq.dq_report_builders import build_summary
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    DQThresholds,
    MedallionLayer,
    SilverDQReport,
)


class SilverDQReportAssemblerService:
    """Build report-level structures for Silver DQ output."""

    def calculate_thresholds(
        self,
        df_len: int,
        input_record_count: int | None,
        quarantined_count: int,
        soft_fail_threshold: float,
        hard_fail_threshold: float,
    ) -> DQThresholds:
        """Calculate DQ thresholds and threshold status."""
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

    def assemble_report(
        self,
        *,
        run_id: str,
        pipeline: str,
        target_table: str,
        source_batch_ids: list[str],
        timestamp: datetime,
        checks: dict[str, object],
        thresholds: DQThresholds,
        passed: int,
        failed: int,
        warnings: int,
    ) -> SilverDQReport:
        """Assemble Silver DQ report with summary from counters."""
        summary = build_summary(
            passed=passed,
            failed=failed,
            warnings=warnings,
            threshold_status=thresholds.threshold_status,
        )

        return SilverDQReport(
            layer=MedallionLayer.SILVER,
            timestamp=timestamp,
            run_id=run_id,
            pipeline=pipeline,
            source_batch_ids=tuple(source_batch_ids),
            target_table=target_table,
            checks=checks,
            thresholds=thresholds,
            summary=summary,
        )


__all__ = ["SilverDQReportAssemblerService"]
