"""Gold layer DQ analyzer.

Orchestrates strict validation for Gold data marts by delegating to
specialized check modules:
- _checks_basic: record count, completeness, data freshness
- _checks_business: business rules validation
- _checks_integrity: referential integrity, SCD integrity
- _checks_statistical: statistical profiling, anomaly detection

Follows RULES.md §3.1 DQ strategy for Gold layer.

Split from monolithic 761-LOC class per audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl
import pyarrow as pa

from bioetl.application.services.dq._checks_basic import (
    check_completeness,
    check_data_freshness,
    check_record_count,
)
from bioetl.application.services.dq._checks_business import check_business_rules
from bioetl.application.services.dq._checks_integrity import (
    check_referential_integrity,
    check_scd_integrity,
)
from bioetl.application.services.dq._checks_statistical import (
    check_anomaly_detection,
    check_statistical_profile,
)
from bioetl.application.services.dq.dq_report_builders import (
    build_summary,
    update_counts,
)
from bioetl.domain.ports import GoldDQConfigPort
from bioetl.domain.services.dq_serializer import to_dict
from bioetl.domain.value_objects.dq_report import (
    GoldDQCheckType,
    GoldDQReport,
    MedallionLayer,
)


class GoldDQAnalyzer:
    """Analyzer for Gold layer DQ checks.

    Performs strict validation on data marts for business-critical metrics.
    Implements GoldDQAnalyzerPort.

    Delegates individual checks to specialized modules in
    ``_checks_basic``, ``_checks_business``, ``_checks_integrity``,
    ``_checks_statistical``.
    """

    def _execute_checks(
        self,
        df: pl.DataFrame,
        enabled_checks: set[GoldDQCheckType],
        required_fields: list[str],
        completeness_threshold: float,
        business_rules: list[dict[str, Any]],  # Any: DQ check values vary by check type
        reference_tables: dict[str, pl.DataFrame | pa.Table],
        baseline_stats: dict[str, Any]
        | None,  # Any: DQ check values vary by check type
        scd_config: dict[str, Any] | None,  # Any: DQ check values vary by check type
    ) -> tuple[
        dict[str, Any], int, int, int
    ]:  # Any: DQ check values vary by check type
        """Execute all enabled DQ checks and collect results."""
        checks: dict[str, Any] = {}  # Any: DQ check values vary by check type
        passed, failed, warnings = 0, 0, 0

        if GoldDQCheckType.RECORD_COUNT in enabled_checks:
            rc = check_record_count(df, baseline_stats)
            checks["record_count"] = to_dict(rc)
            passed, failed, warnings = update_counts(
                rc.status, passed, failed, warnings
            )

        if GoldDQCheckType.COMPLETENESS in enabled_checks:
            comp = check_completeness(df, required_fields, completeness_threshold)
            checks["completeness"] = to_dict(comp)
            passed, failed, warnings = update_counts(
                comp.status, passed, failed, warnings
            )

        if GoldDQCheckType.BUSINESS_RULES in enabled_checks:
            br = check_business_rules(df, business_rules)
            checks["business_rules"] = to_dict(br)
            passed, failed, warnings = update_counts(
                br.status, passed, failed, warnings
            )

        if GoldDQCheckType.REFERENTIAL_INTEGRITY in enabled_checks:
            ri = check_referential_integrity(df, reference_tables)
            checks["referential_integrity"] = to_dict(ri)
            passed, failed, warnings = update_counts(
                ri.status, passed, failed, warnings
            )

        if GoldDQCheckType.STATISTICAL_PROFILE in enabled_checks:
            sp = check_statistical_profile(df, baseline_stats)
            checks["statistical_profile"] = to_dict(sp)
            passed, failed, warnings = update_counts(
                sp.status, passed, failed, warnings
            )

        if GoldDQCheckType.ANOMALY_DETECTION in enabled_checks:
            ad = check_anomaly_detection(df, baseline_stats)
            checks["anomaly_detection"] = to_dict(ad)
            passed, failed, warnings = update_counts(
                ad.status, passed, failed, warnings
            )

        if GoldDQCheckType.SCD_INTEGRITY in enabled_checks:
            scd = check_scd_integrity(df, scd_config)
            checks["scd_integrity"] = to_dict(scd)
            passed, failed, warnings = update_counts(
                scd.status, passed, failed, warnings
            )

        return checks, passed, failed, warnings

    def analyze(
        self,
        data: pl.DataFrame | pa.Table,
        *,
        run_id: str,
        pipeline: str,
        target_table: str,
        config: GoldDQConfigPort,
        timestamp: datetime,
        required_fields: list[str] | None = None,
        completeness_threshold: float = 0.90,
        business_rules: list[dict[str, Any]]
        | None = None,  # Any: DQ check values vary by check type
        reference_tables: dict[str, pl.DataFrame | pa.Table] | None = None,
        baseline_stats: dict[str, Any]
        | None = None,  # Any: DQ check values vary by check type
        scd_config: dict[str, Any]
        | None = None,  # Any: DQ check values vary by check type
    ) -> GoldDQReport:
        """Analyze Gold data and generate DQ report.

        Args:
            data: Polars DataFrame or PyArrow Table with Gold data.
            run_id: Pipeline run identifier.
            pipeline: Pipeline name.
            target_table: Gold table path.
            config: DQ report configuration.
            timestamp: Report generation timestamp (UTC).
            required_fields: List of required fields for completeness.
            completeness_threshold: Minimum completeness score threshold.
            business_rules: List of business rule definitions.
            reference_tables: Tables for referential integrity checks.
            baseline_stats: Historical baseline for anomaly detection.
            scd_config: SCD configuration if applicable.

        Returns:
            GoldDQReport: Complete DQ report for Gold layer.
        """
        if isinstance(data, pa.Table):
            df: pl.DataFrame = pl.from_arrow(data)  # type: ignore[assignment]
        else:
            df = data

        enabled_checks = set(config.get_checks_enums())

        checks, passed, failed, warnings = self._execute_checks(
            df=df,
            enabled_checks=enabled_checks,
            required_fields=required_fields or [],
            completeness_threshold=completeness_threshold,
            business_rules=business_rules or [],
            reference_tables=reference_tables or {},
            baseline_stats=baseline_stats,
            scd_config=scd_config,
        )

        data_freshness = check_data_freshness(df, timestamp)
        summary = build_summary(passed, failed, warnings)

        return GoldDQReport(
            layer=MedallionLayer.GOLD,
            timestamp=timestamp,
            run_id=run_id,
            pipeline=pipeline,
            target_table=target_table,
            checks=checks,
            data_freshness=data_freshness,
            summary=summary,
        )


__all__ = ["GoldDQAnalyzer"]
