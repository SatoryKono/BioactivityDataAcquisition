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

from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

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
    run_serialized_checks,
)
from bioetl.domain.behavior.dq_serializer import to_dict
from bioetl.domain.ports import GoldDQConfigPort
from bioetl.domain.types import (
    GOLD_CONTRACT_VERSION_UNKNOWN,
    GoldBusinessRuleSpec,
    JsonDict,
    ScdConfig,
)
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
        business_rules: list[GoldBusinessRuleSpec],
        reference_tables: dict[str, pl.DataFrame | pa.Table],
        baseline_stats: (
            dict[str, Any]  # Any: DQ baseline statistics have heterogeneous values
            | None
        ),
        scd_config: ScdConfig | None,
        contract_version: str | None,
    ) -> tuple[
        JsonDict, int, int, int  # Any: DQ check values vary by check type
    ]:  # Any: DQ check values vary by check type
        """Execute all enabled DQ checks and collect results."""
        checks: JsonDict = {}  # Any: DQ check values vary by check type
        passed, failed, warnings = 0, 0, 0

        dispatch: list[
            tuple[GoldDQCheckType, str, Callable[[], Any]]  # Any: check results vary
        ] = [
            (
                GoldDQCheckType.RECORD_COUNT,
                "record_count",
                lambda: check_record_count(df, baseline_stats),
            ),
            (
                GoldDQCheckType.COMPLETENESS,
                "completeness",
                lambda: check_completeness(
                    df,
                    required_fields,
                    completeness_threshold,
                    contract_version=contract_version,
                ),
            ),
            (
                GoldDQCheckType.BUSINESS_RULES,
                "business_rules",
                lambda: check_business_rules(
                    df,
                    business_rules,
                    contract_version=contract_version,
                ),
            ),
            (
                GoldDQCheckType.REFERENTIAL_INTEGRITY,
                "referential_integrity",
                lambda: check_referential_integrity(
                    df,
                    reference_tables,
                    contract_version=contract_version,
                ),
            ),
            (
                GoldDQCheckType.STATISTICAL_PROFILE,
                "statistical_profile",
                lambda: check_statistical_profile(df, baseline_stats),
            ),
            (
                GoldDQCheckType.ANOMALY_DETECTION,
                "anomaly_detection",
                lambda: check_anomaly_detection(df, baseline_stats),
            ),
            (
                GoldDQCheckType.SCD_INTEGRITY,
                "scd_integrity",
                lambda: check_scd_integrity(df, scd_config),
            ),
        ]
        passed, failed, warnings = run_serialized_checks(
            enabled_checks=enabled_checks,
            dispatch=dispatch,
            checks=checks,
            serialize_result=to_dict,
            passed=passed,
            failed=failed,
            warnings=warnings,
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
        business_rules: (list[GoldBusinessRuleSpec] | None) = None,
        reference_tables: dict[str, pl.DataFrame | pa.Table] | None = None,
        baseline_stats: (
            dict[
                str, Any  # Any: DQ check values vary by check type
            ]  # Any: DQ baseline statistics have heterogeneous values
            | None
        ) = None,  # Any: DQ check values vary by check type
        scd_config: ScdConfig | None = None,
        contract_version: str | None = GOLD_CONTRACT_VERSION_UNKNOWN,
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
            contract_version: Gold contract version for reject reason payloads.

        Returns:
            GoldDQReport: Complete DQ report for Gold layer.
        """
        df = (
            cast("pl.DataFrame", pl.from_arrow(data))
            if isinstance(data, pa.Table)
            else data
        )

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
            contract_version=contract_version,
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
