"""Silver DQ report formatting component."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bioetl.application.services.dq.dq_report_builders import build_summary
from bioetl.domain.services.dq_serializer import to_dict
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    DQThresholds,
    MedallionLayer,
    SilverDQReport,
    ValueDistributionResult,
)


class DQReportFormatter:
    """Build report-level payloads for Silver DQ analysis."""

    def format_distribution(
        self, result: ValueDistributionResult
    ) -> dict[str, Any]:  # Any: DQ check values vary by check type
        """Convert ValueDistributionResult to report dictionary."""
        output: dict[str, Any] = {  # Any: DQ check values vary by check type
            "numeric_columns": {},
            "categorical_columns": {},
            "status": result.status.value,
        }

        for col, numeric_dist in result.numeric_columns.items():
            output["numeric_columns"][col] = to_dict(numeric_dist)

        for col, categorical_dist in result.categorical_columns.items():
            output["categorical_columns"][col] = {
                "top_values": list(categorical_dist.top_values),
                "cardinality": categorical_dist.cardinality,
            }

        return output

    def build_report(
        self,
        *,
        timestamp: datetime,
        run_id: str,
        pipeline: str,
        source_batch_ids: list[str],
        target_table: str,
        checks: dict[str, Any],  # Any: DQ check values vary by check type
        thresholds: DQThresholds,
        passed: int,
        failed: int,
        warnings: int,
    ) -> SilverDQReport:
        """Build final SilverDQReport from collected parts."""
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

    def update_distribution_checks(
        self,
        checks: dict[str, Any],  # Any: DQ check values vary by check type
    ) -> dict[str, Any]:  # Any: DQ check values vary by check type
        """Normalize serialized distribution payloads in check dictionary."""
        distribution = checks.get("value_distribution")
        if isinstance(distribution, ValueDistributionResult):
            checks["value_distribution"] = self.format_distribution(distribution)
        return checks

    def get_distribution_status(self, checks: dict[str, Any]) -> DQCheckStatus | None:
        """Extract distribution status when available."""
        distribution = checks.get("value_distribution")
        if isinstance(distribution, dict):
            status = distribution.get("status")
            if isinstance(status, str):
                return DQCheckStatus(status)
        return None


__all__ = ["DQReportFormatter"]
