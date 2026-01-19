"""Gold layer DQ analyzer.

Implements strict validation for Gold data marts:
- Record count with baseline comparison
- Completeness checks for required fields
- Business rules validation
- Referential integrity checks
- Statistical profiling with MA30 baseline
- Anomaly detection
- SCD (Slowly Changing Dimension) integrity

Follows RULES.md §3.1 DQ strategy for Gold layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl
import pyarrow as pa

from bioetl.domain.ports.dq_config import GoldDQConfigPort
from bioetl.domain.value_objects.dq_report import (
    AnomalyDetectionResult,
    AnomalyMetric,
    BusinessRuleResult,
    BusinessRulesResult,
    CompletenessResult,
    DataFreshnessResult,
    DQCheckStatus,
    DQReportStatus,
    DQReportSummary,
    ForeignKeyResult,
    GoldDQCheckType,
    GoldDQReport,
    MedallionLayer,
    RecordCountResult,
    ReferentialIntegrityResult,
    SCDIntegrityResult,
    StatisticalMetric,
    StatisticalProfileResult,
)


class GoldDQAnalyzer:
    """Analyzer for Gold layer DQ checks.

    Performs strict validation on data marts for business-critical metrics.
    Implements GoldDQAnalyzerPort.
    """

    # Anomaly detection thresholds from RULES.md §3.4.1
    NULL_RATE_WARNING_MULTIPLIER = 2.0
    NULL_RATE_CRITICAL_MULTIPLIER = 5.0
    RECORD_COUNT_WARNING_THRESHOLD = 0.70
    RECORD_COUNT_CRITICAL_THRESHOLD = 0.50
    FRESHNESS_WARNING_HOURS = 24
    FRESHNESS_CRITICAL_HOURS = 72

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
        business_rules: list[dict[str, Any]] | None = None,
        reference_tables: dict[str, pl.DataFrame | pa.Table] | None = None,
        baseline_stats: dict[str, Any] | None = None,
        scd_config: dict[str, Any] | None = None,
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
        # Convert PyArrow to Polars for consistent processing
        if isinstance(data, pa.Table):
            df: pl.DataFrame = pl.from_arrow(data)  # type: ignore[assignment]
        else:
            df = data

        enabled_checks = set(config.get_checks_enums())

        checks: dict[str, Any] = {}
        passed = 0
        failed = 0
        warnings = 0

        # Record count check
        if GoldDQCheckType.RECORD_COUNT in enabled_checks:
            record_count_result = self._check_record_count(df, baseline_stats)
            checks["record_count"] = self._result_to_dict(record_count_result)
            passed, failed, warnings = self._update_counts(
                record_count_result.status, passed, failed, warnings
            )

        # Completeness check
        if GoldDQCheckType.COMPLETENESS in enabled_checks:
            completeness_result = self._check_completeness(
                df, required_fields or [], completeness_threshold
            )
            checks["completeness"] = self._result_to_dict(completeness_result)
            passed, failed, warnings = self._update_counts(
                completeness_result.status, passed, failed, warnings
            )

        # Business rules check
        if GoldDQCheckType.BUSINESS_RULES in enabled_checks:
            business_rules_result = self._check_business_rules(df, business_rules or [])
            checks["business_rules"] = self._business_rules_to_dict(
                business_rules_result
            )
            passed, failed, warnings = self._update_counts(
                business_rules_result.status, passed, failed, warnings
            )

        # Referential integrity check
        if GoldDQCheckType.REFERENTIAL_INTEGRITY in enabled_checks:
            ref_integrity_result = self._check_referential_integrity(
                df, reference_tables or {}
            )
            checks["referential_integrity"] = self._ref_integrity_to_dict(
                ref_integrity_result
            )
            passed, failed, warnings = self._update_counts(
                ref_integrity_result.status, passed, failed, warnings
            )

        # Statistical profile check
        if GoldDQCheckType.STATISTICAL_PROFILE in enabled_checks:
            stat_profile_result = self._check_statistical_profile(df, baseline_stats)
            checks["statistical_profile"] = self._stat_profile_to_dict(
                stat_profile_result
            )
            passed, failed, warnings = self._update_counts(
                stat_profile_result.status, passed, failed, warnings
            )

        # Anomaly detection
        if GoldDQCheckType.ANOMALY_DETECTION in enabled_checks:
            anomaly_result = self._check_anomaly_detection(df, baseline_stats)
            checks["anomaly_detection"] = self._anomaly_to_dict(anomaly_result)
            passed, failed, warnings = self._update_counts(
                anomaly_result.status, passed, failed, warnings
            )

        # SCD integrity check
        if GoldDQCheckType.SCD_INTEGRITY in enabled_checks:
            scd_result = self._check_scd_integrity(df, scd_config)
            checks["scd_integrity"] = self._result_to_dict(scd_result)
            passed, failed, warnings = self._update_counts(
                scd_result.status, passed, failed, warnings
            )

        total_checks = passed + failed + warnings

        # Data freshness check
        data_freshness = self._check_data_freshness(df, timestamp)

        # Determine overall status
        if failed > 0:
            overall_status = DQReportStatus.FAIL
        elif warnings > 0:
            overall_status = DQReportStatus.WARNING
        else:
            overall_status = DQReportStatus.PASS

        summary = DQReportSummary(
            total_checks=total_checks,
            passed=passed,
            failed=failed,
            warnings=warnings,
            overall_status=overall_status,
        )

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

    def _check_record_count(
        self, df: pl.DataFrame, baseline_stats: dict[str, Any] | None
    ) -> RecordCountResult:
        """Check record count against baseline."""
        current = len(df)
        baseline = (
            baseline_stats.get("record_count_ma30", current)
            if baseline_stats
            else current
        )
        delta = (current - baseline) / baseline if baseline > 0 else 0.0

        # Check for significant drop
        status = DQCheckStatus.PASS
        if delta < -0.5:  # >50% drop
            status = DQCheckStatus.FAIL
        elif delta < -0.3:  # >30% drop
            status = DQCheckStatus.WARN

        return RecordCountResult(
            value=current,
            status=status,
            delta_from_last_run=int(current - baseline) if baseline else None,
        )

    def _check_completeness(
        self,
        df: pl.DataFrame,
        required_fields: list[str],
        threshold: float,
    ) -> CompletenessResult:
        """Check completeness of required fields."""
        if not required_fields:
            return CompletenessResult(
                required_fields={},
                overall_completeness_score=1.0,
                minimum_threshold=threshold,
                status=DQCheckStatus.PASS,
            )

        field_rates = {}
        total_rate = 0.0
        count = 0

        for field in required_fields:
            if field in df.columns:
                null_count = df[field].null_count()
                rate = 1.0 - (null_count / len(df)) if len(df) > 0 else 0.0
                field_rates[field] = round(rate, 4)
                total_rate += rate
                count += 1
            else:
                field_rates[field] = 0.0

        overall_score = total_rate / count if count > 0 else 0.0

        status = (
            DQCheckStatus.PASS if overall_score >= threshold else DQCheckStatus.FAIL
        )

        return CompletenessResult(
            required_fields=field_rates,
            overall_completeness_score=round(overall_score, 4),
            minimum_threshold=threshold,
            status=status,
        )

    def _check_not_null_rule(
        self, df: pl.DataFrame, column: str
    ) -> tuple[bool, int | None]:
        """Check not_null rule for a column."""
        violations = df[column].null_count()
        return violations == 0, violations

    def _check_range_rule(
        self,
        df: pl.DataFrame,
        column: str,
        min_val: Any | None,
        max_val: Any | None,
    ) -> tuple[bool, int]:
        """Check range rule for a column."""
        violations = 0
        col_data = df[column].drop_nulls()
        if min_val is not None:
            violations += (col_data < min_val).sum()
        if max_val is not None:
            violations += (col_data > max_val).sum()
        return violations == 0, violations

    def _check_in_list_rule(
        self, df: pl.DataFrame, column: str, allowed: list[Any]
    ) -> tuple[bool, int | None]:
        """Check in_list rule for a column."""
        if not allowed:
            return True, 0
        violations = int((~df[column].is_in(allowed)).sum())
        return violations == 0, violations

    def _check_regex_rule(
        self, df: pl.DataFrame, column: str, pattern: str
    ) -> tuple[bool, int | None]:
        """Check regex rule for a column."""
        if not pattern:
            return True, 0
        violations = int((~df[column].str.contains(pattern, literal=False)).sum())
        return violations == 0, violations

    def _evaluate_single_rule(
        self, df: pl.DataFrame, rule: dict[str, Any]
    ) -> tuple[bool, int | None]:
        """Evaluate a single business rule."""
        column = rule.get("column")
        condition = rule.get("condition")

        if not column or column not in df.columns:
            return True, 0

        if condition == "not_null":
            return self._check_not_null_rule(df, column)
        if condition == "range":
            return self._check_range_rule(
                df, column, rule.get("min"), rule.get("max")
            )
        if condition == "in_list":
            return self._check_in_list_rule(df, column, rule.get("values", []))
        if condition == "regex":
            return self._check_regex_rule(df, column, rule.get("pattern", ""))
        return True, 0

    def _check_business_rules(
        self, df: pl.DataFrame, rules: list[dict[str, Any]]
    ) -> BusinessRulesResult:
        """Validate business rules."""
        if not rules:
            return BusinessRulesResult(
                rules_evaluated=0,
                rules_passed=0,
                rules_failed=0,
                rules=(),
                status=DQCheckStatus.PASS,
            )

        results = []
        rules_passed = 0
        rules_failed = 0

        for rule in rules:
            try:
                passed, violations = self._evaluate_single_rule(df, rule)
            except Exception:
                passed, violations = False, None

            if passed:
                rules_passed += 1
            else:
                rules_failed += 1

            results.append(
                BusinessRuleResult(
                    rule_id=rule.get("rule_id", ""),
                    name=rule.get("name", ""),
                    description=rule.get("description", ""),
                    passed=passed,
                    violations=violations,
                )
            )

        status = DQCheckStatus.PASS if rules_failed == 0 else DQCheckStatus.FAIL

        return BusinessRulesResult(
            rules_evaluated=len(rules),
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            rules=tuple(results),
            status=status,
        )

    def _check_referential_integrity(
        self, df: pl.DataFrame, reference_tables: dict[str, pl.DataFrame | pa.Table]
    ) -> ReferentialIntegrityResult:
        """Check foreign key references."""
        if not reference_tables:
            return ReferentialIntegrityResult(
                foreign_keys={},
                status=DQCheckStatus.PASS,
            )

        fk_results: dict[str, ForeignKeyResult] = {}
        has_failures = False
        has_warnings = False

        for ref_key, ref_table in reference_tables.items():
            # Parse reference: "local_col -> ref_table.ref_col"
            parts = ref_key.split("->")
            if len(parts) != 2:
                continue

            local_col = parts[0].strip()
            ref_parts = parts[1].strip().split(".")
            if len(ref_parts) != 2:
                continue

            ref_col = ref_parts[1]

            if local_col not in df.columns:
                continue

            # Convert reference table to Polars if needed
            if isinstance(ref_table, pa.Table):
                ref_df: pl.DataFrame = pl.from_arrow(ref_table)  # type: ignore[assignment]
            else:
                ref_df = ref_table

            if ref_col not in ref_df.columns:
                continue

            # Count references
            local_values = df[local_col].drop_nulls()
            ref_values = ref_df[ref_col].unique()

            total_refs = len(local_values)
            valid_refs = int(local_values.is_in(ref_values).sum())
            orphans = total_refs - valid_refs

            if orphans > 0:
                if orphans / total_refs > 0.01:  # >1% orphans
                    status = DQCheckStatus.FAIL
                    has_failures = True
                else:
                    status = DQCheckStatus.WARN
                    has_warnings = True
            else:
                status = DQCheckStatus.PASS

            fk_results[ref_key] = ForeignKeyResult(
                reference=ref_key,
                total_references=total_refs,
                valid_references=valid_refs,
                orphan_records=orphans,
                status=status,
            )

        overall_status = DQCheckStatus.PASS
        if has_failures:
            overall_status = DQCheckStatus.FAIL
        elif has_warnings:
            overall_status = DQCheckStatus.WARN

        return ReferentialIntegrityResult(
            foreign_keys=fk_results,
            status=overall_status,
        )

    def _check_statistical_profile(
        self, df: pl.DataFrame, baseline_stats: dict[str, Any] | None
    ) -> StatisticalProfileResult:
        """Compare statistics against baseline (MA30)."""
        if not baseline_stats:
            return StatisticalProfileResult(
                baseline_period_days=30,
                metrics={},
                status=DQCheckStatus.PASS,
            )

        metrics: dict[str, StatisticalMetric] = {}

        # Check null rate
        if "null_rate_ma30" in baseline_stats:
            total_nulls = sum(df[col].null_count() for col in df.columns)
            total_cells = len(df) * len(df.columns)
            current_null_rate = total_nulls / total_cells if total_cells > 0 else 0.0
            baseline_null_rate = baseline_stats["null_rate_ma30"]

            ratio = (
                current_null_rate / baseline_null_rate
                if baseline_null_rate > 0
                else 1.0
            )

            if ratio > self.NULL_RATE_CRITICAL_MULTIPLIER:
                status = DQCheckStatus.FAIL
            elif ratio > self.NULL_RATE_WARNING_MULTIPLIER:
                status = DQCheckStatus.WARN
            else:
                status = DQCheckStatus.PASS

            metrics["null_rate_avg"] = StatisticalMetric(
                current=round(current_null_rate, 4),
                baseline=round(baseline_null_rate, 4),
                ratio=round(ratio, 4),
                threshold_warning=self.NULL_RATE_WARNING_MULTIPLIER,
                threshold_critical=self.NULL_RATE_CRITICAL_MULTIPLIER,
                status=status,
            )

        # Check record count
        if "record_count_ma30" in baseline_stats:
            current_count = len(df)
            baseline_count = baseline_stats["record_count_ma30"]

            ratio = current_count / baseline_count if baseline_count > 0 else 1.0

            if ratio < self.RECORD_COUNT_CRITICAL_THRESHOLD:
                status = DQCheckStatus.FAIL
            elif ratio < self.RECORD_COUNT_WARNING_THRESHOLD:
                status = DQCheckStatus.WARN
            else:
                status = DQCheckStatus.PASS

            metrics["record_count_daily"] = StatisticalMetric(
                current=float(current_count),
                baseline=float(baseline_count),
                ratio=round(ratio, 4),
                threshold_warning=self.RECORD_COUNT_WARNING_THRESHOLD,
                threshold_critical=self.RECORD_COUNT_CRITICAL_THRESHOLD,
                status=status,
            )

        overall_status = DQCheckStatus.PASS
        for metric in metrics.values():
            if metric.status == DQCheckStatus.FAIL:
                overall_status = DQCheckStatus.FAIL
                break
            elif metric.status == DQCheckStatus.WARN:
                overall_status = DQCheckStatus.WARN

        return StatisticalProfileResult(
            baseline_period_days=30,
            metrics=metrics,
            status=overall_status,
        )

    def _check_anomaly_detection(
        self, df: pl.DataFrame, baseline_stats: dict[str, Any] | None
    ) -> AnomalyDetectionResult:
        """Detect anomalies using baseline comparison."""
        cold_start_days = 30
        current_day = baseline_stats.get("days_since_start", 0) if baseline_stats else 0
        cold_start_mode = current_day < cold_start_days

        if cold_start_mode or not baseline_stats:
            return AnomalyDetectionResult(
                cold_start_days=cold_start_days,
                current_day=current_day,
                cold_start_mode=True,
                anomalies_detected=(),
                metrics_monitored=(),
                status=DQCheckStatus.PASS,
            )

        anomalies = []
        metrics_monitored = []

        # Check null rate anomaly
        total_nulls = sum(df[col].null_count() for col in df.columns)
        total_cells = len(df) * len(df.columns)
        current_null_rate = total_nulls / total_cells if total_cells > 0 else 0.0
        baseline_null_rate = baseline_stats.get("null_rate_ma30", current_null_rate)

        null_zscore = (
            (current_null_rate - baseline_null_rate) / baseline_null_rate
            if baseline_null_rate > 0
            else 0.0
        )

        if abs(null_zscore) > 3:
            anomalies.append("null_rate")
            null_status = "anomaly"
        else:
            null_status = "normal"

        metrics_monitored.append(
            AnomalyMetric(
                metric="null_rate",
                current_value=round(current_null_rate, 4),
                baseline_value=round(baseline_null_rate, 4),
                zscore=round(null_zscore, 2),
                status=null_status,
            )
        )

        # Check record count anomaly
        current_count = float(len(df))
        baseline_count = baseline_stats.get("record_count_ma30", current_count)
        count_zscore = (
            (current_count - baseline_count) / baseline_count
            if baseline_count > 0
            else 0.0
        )

        if abs(count_zscore) > 3:
            anomalies.append("record_count")
            count_status = "anomaly"
        else:
            count_status = "normal"

        metrics_monitored.append(
            AnomalyMetric(
                metric="record_count",
                current_value=current_count,
                baseline_value=baseline_count,
                zscore=round(count_zscore, 2),
                status=count_status,
            )
        )

        status = DQCheckStatus.WARN if anomalies else DQCheckStatus.PASS

        return AnomalyDetectionResult(
            cold_start_days=cold_start_days,
            current_day=current_day,
            cold_start_mode=False,
            anomalies_detected=tuple(anomalies),
            metrics_monitored=tuple(metrics_monitored),
            status=status,
        )

    def _check_scd_integrity(
        self, df: pl.DataFrame, scd_config: dict[str, Any] | None
    ) -> SCDIntegrityResult:
        """Check SCD (Slowly Changing Dimension) integrity."""
        if not scd_config:
            return SCDIntegrityResult(
                scd_type=2,
                total_entities=len(df),
                entities_with_history=0,
                avg_versions_per_entity=1.0,
                version_gaps=0,
                temporal_conflicts=0,
                overlapping_validity_periods=0,
                status=DQCheckStatus.PASS,
            )

        scd_type = scd_config.get("type", 2)
        entity_key = scd_config.get("entity_key")
        valid_from = scd_config.get("valid_from_col", "_valid_from")
        valid_to = scd_config.get("valid_to_col", "_valid_to")

        if not entity_key or entity_key not in df.columns:
            return SCDIntegrityResult(
                scd_type=scd_type,
                total_entities=len(df),
                entities_with_history=0,
                avg_versions_per_entity=1.0,
                version_gaps=0,
                temporal_conflicts=0,
                overlapping_validity_periods=0,
                status=DQCheckStatus.PASS,
            )

        # Count unique entities
        unique_entities = df[entity_key].n_unique()
        total_records = len(df)

        # Entities with multiple versions
        version_counts = df.group_by(entity_key).agg(pl.count().alias("versions"))
        entities_with_history = int((version_counts["versions"] > 1).sum())
        avg_versions = total_records / unique_entities if unique_entities > 0 else 1.0

        # Check temporal integrity if columns exist
        version_gaps = 0
        temporal_conflicts = 0
        overlapping = 0

        if valid_from in df.columns and valid_to in df.columns:
            # Check for overlapping validity periods
            # This is a simplified check
            try:
                for entity in df[entity_key].unique().to_list()[:100]:  # Sample
                    entity_records = df.filter(pl.col(entity_key) == entity).sort(
                        valid_from
                    )
                    if len(entity_records) > 1:
                        # Check for overlaps
                        for i in range(len(entity_records) - 1):
                            current_to = entity_records[valid_to][i]
                            next_from = entity_records[valid_from][i + 1]
                            if (
                                current_to is not None
                                and next_from is not None
                                and current_to > next_from
                            ):
                                overlapping += 1
            except Exception:
                pass

        status = DQCheckStatus.PASS if overlapping == 0 else DQCheckStatus.WARN

        return SCDIntegrityResult(
            scd_type=scd_type,
            total_entities=unique_entities,
            entities_with_history=entities_with_history,
            avg_versions_per_entity=round(avg_versions, 2),
            version_gaps=version_gaps,
            temporal_conflicts=temporal_conflicts,
            overlapping_validity_periods=overlapping,
            status=status,
        )

    def _check_data_freshness(
        self, df: pl.DataFrame, current_time: datetime
    ) -> DataFreshnessResult:
        """Check data freshness based on timestamp columns."""
        # Try to find timestamp column
        timestamp_cols = ["_updated_at", "updated_at", "_ingestion_ts", "created_at"]
        max_ts = None

        for col in timestamp_cols:
            if col in df.columns:
                try:
                    col_max = df[col].max()
                    if col_max is not None:
                        if isinstance(col_max, datetime):
                            max_ts = col_max
                        break
                except Exception:
                    pass

        if max_ts is None:
            return DataFreshnessResult(
                max_updated_at=None,
                freshness_lag_seconds=0.0,
                freshness_lag_hours=0.0,
                status=DQCheckStatus.PASS,
            )

        # Calculate lag
        lag_seconds = (current_time - max_ts).total_seconds()
        lag_hours = lag_seconds / 3600

        if lag_hours > self.FRESHNESS_CRITICAL_HOURS:
            status = DQCheckStatus.FAIL
        elif lag_hours > self.FRESHNESS_WARNING_HOURS:
            status = DQCheckStatus.WARN
        else:
            status = DQCheckStatus.PASS

        return DataFreshnessResult(
            max_updated_at=max_ts,
            freshness_lag_seconds=round(lag_seconds, 2),
            freshness_lag_hours=round(lag_hours, 2),
            status=status,
        )

    def _result_to_dict(self, result: Any) -> dict[str, Any]:
        """Convert dataclass result to dict for serialization."""
        if hasattr(result, "__dataclass_fields__"):
            output = {}
            for field in result.__dataclass_fields__:
                if field.startswith("_"):
                    continue
                value = getattr(result, field)
                if hasattr(value, "value"):  # Enum
                    output[field] = value.value
                elif hasattr(value, "__dataclass_fields__"):
                    output[field] = self._result_to_dict(value)
                elif isinstance(value, datetime):
                    output[field] = value.isoformat()
                else:
                    output[field] = value
            return output
        return {"value": result}

    def _business_rules_to_dict(self, result: BusinessRulesResult) -> dict[str, Any]:
        """Convert business rules result to dict."""
        return {
            "rules_evaluated": result.rules_evaluated,
            "rules_passed": result.rules_passed,
            "rules_failed": result.rules_failed,
            "rules": [self._result_to_dict(r) for r in result.rules],
            "status": result.status.value,
        }

    def _ref_integrity_to_dict(
        self, result: ReferentialIntegrityResult
    ) -> dict[str, Any]:
        """Convert referential integrity result to dict."""
        return {
            "foreign_keys": {
                k: self._result_to_dict(v) for k, v in result.foreign_keys.items()
            },
            "status": result.status.value,
        }

    def _stat_profile_to_dict(self, result: StatisticalProfileResult) -> dict[str, Any]:
        """Convert statistical profile result to dict."""
        return {
            "baseline_period_days": result.baseline_period_days,
            "metrics": {k: self._result_to_dict(v) for k, v in result.metrics.items()},
            "status": result.status.value,
        }

    def _anomaly_to_dict(self, result: AnomalyDetectionResult) -> dict[str, Any]:
        """Convert anomaly detection result to dict."""
        return {
            "cold_start_days": result.cold_start_days,
            "current_day": result.current_day,
            "cold_start_mode": result.cold_start_mode,
            "anomalies_detected": list(result.anomalies_detected),
            "metrics_monitored": [
                self._result_to_dict(m) for m in result.metrics_monitored
            ],
            "status": result.status.value,
        }

    def _update_counts(
        self,
        status: DQCheckStatus,
        passed: int,
        failed: int,
        warnings: int,
    ) -> tuple[int, int, int]:
        """Update check counts based on status."""
        if status == DQCheckStatus.PASS:
            return passed + 1, failed, warnings
        elif status == DQCheckStatus.FAIL:
            return passed, failed + 1, warnings
        else:  # WARN
            return passed, failed, warnings + 1


__all__ = ["GoldDQAnalyzer"]
