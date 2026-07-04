"""Silver layer DQ analyzer facade.

Orchestrates data quality monitoring for normalized Silver data by
delegating to focused components:
- SilverStatisticsCalculator: check metric computations
- SilverThresholdChecker: error rate thresholds and key constraints

Implements SilverDQAnalyzerPort. Follows RULES.md §3.1 DQ strategy.
"""

from __future__ import annotations

from datetime import datetime

import polars as pl
import pyarrow as pa

from bioetl.application.services.dq.dq_report_builders import build_summary
from bioetl.application.services.dq.silver_check_executor import SilverCheckExecutor
from bioetl.application.services.dq.silver_statistics import SilverStatisticsCalculator
from bioetl.application.services.dq.silver_threshold import SilverThresholdChecker
from bioetl.domain.ports import (
    SilverDQAnalyzeRequest,
    coerce_silver_dq_analyze_request,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report import (
    DQReportSummary,
    DQThresholds,
    MedallionLayer,
    SilverDQReport,
)


class SilverDQAnalyzer:
    """Facade for Silver layer DQ checks.

    Orchestrates comprehensive data quality monitoring on normalized data
    by delegating to SilverStatisticsCalculator and SilverThresholdChecker.
    Implements SilverDQAnalyzerPort.
    """

    def __init__(
        self,
        *,
        statistics: SilverStatisticsCalculator,
        threshold_checker: SilverThresholdChecker,
        check_executor: SilverCheckExecutor,
    ) -> None:
        self._statistics = statistics
        self._threshold = threshold_checker
        self._check_executor = check_executor

    def _to_polars_dataframe(self, data: pl.DataFrame | pa.Table) -> pl.DataFrame:
        """Normalize input to Polars DataFrame."""
        if isinstance(data, pa.Table):
            frame = pl.from_arrow(data)
            return frame.to_frame() if isinstance(frame, pl.Series) else frame
        return data

    def _build_report(
        self,
        *,
        timestamp: datetime,
        run_id: str,
        pipeline: str,
        source_batch_ids: list[str],
        target_table: str,
        checks: JsonDict,
        thresholds: DQThresholds,
        summary: DQReportSummary,
    ) -> SilverDQReport:
        """Build immutable SilverDQReport from computed parts."""
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

    def _calculate_thresholds_and_summary(
        self,
        *,
        df: pl.DataFrame,
        input_record_count: int | None,
        quarantined_count: int,
        soft_fail_threshold: float,
        hard_fail_threshold: float,
        passed: int,
        failed: int,
        warnings: int,
    ) -> tuple[DQThresholds, DQReportSummary]:
        """Calculate thresholds and derive aggregate summary."""
        thresholds = self._threshold.calculate_thresholds(
            df_len=len(df),
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            soft_fail_threshold=soft_fail_threshold,
            hard_fail_threshold=hard_fail_threshold,
        )
        summary = build_summary(
            passed=passed,
            failed=failed,
            warnings=warnings,
            threshold_status=thresholds.threshold_status,
        )
        return thresholds, summary

    def analyze(
        self,
        request: SilverDQAnalyzeRequest | pl.DataFrame | pa.Table | None = None,
        *args: object,
        **kwargs: object,
    ) -> SilverDQReport:
        """Analyze Silver data and generate DQ report.

        Args:
            data: Input DataFrame or PyArrow Table to run DQ checks on.
            run_id: Unique run identifier for the report header.
            pipeline: Pipeline name string for the report header.
            target_table: Target Silver table name for the report header.
            source_batch_ids: List of upstream Bronze batch IDs for lineage.
            config: Silver DQ config port controlling which checks are enabled.
            timestamp: Report timestamp (usually the run completion time).
            primary_keys: List of column names that form the entity primary key.
            soft_fail_threshold: Error rate threshold for WARN status (default 5%).
            hard_fail_threshold: Error rate threshold for FAIL status (default 20%).
            input_record_count: Optional count of Bronze input records for
                error rate calculation.
            quarantined_count: Number of records quarantined during transformation.
            previous_schema: Optional schema snapshot from the prior run for
                drift detection.
            key_nullability_rules: Optional list of nullability rule dicts for
                business-key null rate checks.

        Returns:
            SilverDQReport with per-check results, thresholds, and aggregate summary.
        """
        analyze_request = coerce_silver_dq_analyze_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        df = self._to_polars_dataframe(analyze_request.data)
        enabled_checks = set(analyze_request.config.get_checks_enums())
        checks, passed, failed, warnings = self._check_executor.execute_checks(
            df=df,
            enabled_checks=enabled_checks,
            primary_keys=analyze_request.primary_keys,
            input_record_count=analyze_request.input_record_count,
            quarantined_count=analyze_request.quarantined_count,
            previous_schema=analyze_request.previous_schema,
            key_nullability_rules=analyze_request.key_nullability_rules,
        )
        thresholds, summary = self._calculate_thresholds_and_summary(
            df=df,
            input_record_count=analyze_request.input_record_count,
            quarantined_count=analyze_request.quarantined_count,
            soft_fail_threshold=analyze_request.soft_fail_threshold,
            hard_fail_threshold=analyze_request.hard_fail_threshold,
            passed=passed,
            failed=failed,
            warnings=warnings,
        )
        return self._build_report(
            timestamp=analyze_request.timestamp,
            run_id=analyze_request.run_id,
            pipeline=analyze_request.pipeline,
            source_batch_ids=analyze_request.source_batch_ids,
            target_table=analyze_request.target_table,
            checks=checks,
            thresholds=thresholds,
            summary=summary,
        )


__all__ = ["SilverDQAnalyzer"]
