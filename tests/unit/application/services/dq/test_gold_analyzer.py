# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# tests/unit/application/services/dq/test_gold_analyzer.py
"""Unit tests for Gold DQ analyzer.

Tests for GoldDQAnalyzer validation checks including:
- Record count with baseline comparison
- Completeness checks for required fields
- Business rules validation
- Referential integrity checks
- Statistical profiling with MA30 baseline
- AnomalyRecord detection
- SCD (Slowly Changing Dimension) integrity
- Data freshness
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import polars as pl
import pyarrow as pa
import pytest

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
    convert_value,
    update_counts,
)
from bioetl.application.services.dq.gold_analyzer import GoldDQAnalyzer
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    DQReportStatus,
    GoldDQCheckType,
    MedallionLayer,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def gold_analyzer() -> GoldDQAnalyzer:
    """Create GoldDQAnalyzer instance."""
    return GoldDQAnalyzer()


@pytest.fixture
def sample_dataframe() -> pl.DataFrame:
    """Create sample Polars DataFrame for testing."""
    return pl.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["a", "b", "c", "d", "e"],
            "value": [100.0, 200.0, None, 400.0, 500.0],
            "category": ["x", "y", "x", "y", "x"],
            "_updated_at": [
                datetime(2024, 5, 15, 10, 0, tzinfo=UTC),
                datetime(2024, 5, 15, 11, 0, tzinfo=UTC),
                datetime(2024, 5, 15, 12, 0, tzinfo=UTC),
                datetime(2024, 5, 15, 13, 0, tzinfo=UTC),
                datetime(2024, 5, 15, 14, 0, tzinfo=UTC),
            ],
        }
    )


@pytest.fixture
def mock_config() -> MagicMock:
    """Create mock DQ config."""
    config = MagicMock()
    config.get_checks_enums.return_value = [
        GoldDQCheckType.RECORD_COUNT,
        GoldDQCheckType.COMPLETENESS,
        GoldDQCheckType.BUSINESS_RULES,
    ]
    return config


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_convert_value_enum(self) -> None:
        """Convert enum value to string."""
        result = convert_value(DQCheckStatus.PASS)
        assert result == "pass"

    def test_convert_value_dataclass(self) -> None:
        """Convert dataclass to dict."""
        from dataclasses import dataclass

        @dataclass
        class TestClass:
            count: int  # Avoid 'value' name collision with enum check
            name: str

        result = convert_value(TestClass(count=1, name="test"))
        assert isinstance(result, dict)
        assert result["count"] == 1
        assert result["name"] == "test"

    def test_convert_value_datetime(self) -> None:
        """Convert datetime to ISO format."""
        dt = datetime(2024, 5, 15, 10, 30, 0, tzinfo=UTC)
        result = convert_value(dt)
        assert "2024-05-15" in result

    def test_convert_value_list(self) -> None:
        """Convert list recursively."""
        result = convert_value([1, 2, DQCheckStatus.PASS])
        assert result == [1, 2, "pass"]

    def test_convert_value_set(self) -> None:
        """Convert set to list for JSON serialization."""
        result = convert_value({1, 2, 3})
        assert isinstance(result, list)
        assert set(result) == {1, 2, 3}

    def test_convert_value_frozenset(self) -> None:
        """Convert frozenset to list for JSON serialization."""
        result = convert_value(frozenset(["a", "b"]))
        assert isinstance(result, list)
        assert set(result) == {"a", "b"}

    def test_convert_value_dict(self) -> None:
        """Convert dict recursively."""
        result = convert_value({"status": DQCheckStatus.FAIL})
        assert result == {"status": "fail"}

    def test_convert_value_primitive(self) -> None:
        """Primitive values are unchanged."""
        assert convert_value(42) == 42
        assert convert_value("test") == "test"
        assert convert_value(3.14) == pytest.approx(3.14)

    def test_update_counts_pass(self) -> None:
        """Update counts for PASS status."""
        passed, failed, warnings = update_counts(DQCheckStatus.PASS, 0, 0, 0)
        assert passed == 1
        assert failed == 0
        assert warnings == 0

    def test_update_counts_fail(self) -> None:
        """Update counts for FAIL status."""
        passed, failed, warnings = update_counts(DQCheckStatus.FAIL, 0, 0, 0)
        assert passed == 0
        assert failed == 1
        assert warnings == 0

    def test_update_counts_warn(self) -> None:
        """Update counts for WARN status."""
        passed, failed, warnings = update_counts(DQCheckStatus.WARN, 0, 0, 0)
        assert passed == 0
        assert failed == 0
        assert warnings == 1


class TestRecordCountCheck:
    """Tests for record count validation."""

    def test_record_count_pass(self) -> None:
        """Record count check passes with stable count."""
        df = pl.DataFrame({"id": [1, 2, 3, 4, 5]})
        baseline_stats = {"record_count_ma30": 5}

        result = check_record_count(df, baseline_stats)

        assert result.value == 5
        assert result.status == DQCheckStatus.PASS

    def test_record_count_warn_on_drop(self) -> None:
        """Record count check warns on >30% drop."""
        df = pl.DataFrame({"id": [1, 2, 3]})  # 3 records
        baseline_stats = {"record_count_ma30": 5}  # 40% drop

        result = check_record_count(df, baseline_stats)

        assert result.status == DQCheckStatus.WARN

    def test_record_count_fail_on_large_drop(self) -> None:
        """Record count check fails on >50% drop."""
        df = pl.DataFrame({"id": [1, 2]})  # 2 records
        baseline_stats = {"record_count_ma30": 5}  # 60% drop

        result = check_record_count(df, baseline_stats)

        assert result.status == DQCheckStatus.FAIL

    def test_record_count_no_baseline(self) -> None:
        """Record count check passes when no baseline available."""
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_record_count(df, None)

        assert result.value == 3
        assert result.status == DQCheckStatus.PASS


class TestCompletenessCheck:
    """Tests for completeness validation."""

    def test_completeness_pass(self) -> None:
        """Completeness check passes with high fill rate."""
        df = pl.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})

        result = check_completeness(df, ["id", "name"], 0.9)

        assert result.overall_completeness_score == pytest.approx(1.0)
        assert result.status == DQCheckStatus.PASS

    def test_completeness_fail_low_fill(self) -> None:
        """Completeness check fails with low fill rate."""
        df = pl.DataFrame({"id": [1, 2, 3], "name": ["a", None, None]})

        result = check_completeness(
            df,
            ["id", "name"],
            0.9,
            contract_version="1.0.0",
        )

        assert result.overall_completeness_score < 0.9
        assert result.status == DQCheckStatus.FAIL
        assert result.reject_reasons[0].reason_code == "gold_contract_required_failure"
        assert result.reject_reasons[0].contract_version == "1.0.0"
        assert result.reject_reasons[0].rule_id == "gold.contract.required.name"

    def test_completeness_missing_field(self) -> None:
        """Completeness check handles missing required field.

        Note: The implementation only counts existing columns in overall score,
        so missing fields result in 0.0 fill rate but don't reduce overall score
        if other fields have high fill rates. The missing field is still tracked.
        """
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_completeness(df, ["id", "missing_field"], 0.9)

        # Missing field is tracked with 0.0 fill rate
        assert result.required_fields["missing_field"] == pytest.approx(0.0)
        # But overall score only considers existing columns (id has 100% fill)
        # This is expected behavior - overall score = 1.0 / 1 = 1.0
        assert result.overall_completeness_score == pytest.approx(1.0)
        assert result.status == DQCheckStatus.PASS

    def test_completeness_no_required_fields(self) -> None:
        """Completeness check passes when no required fields specified."""
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_completeness(df, [], 0.9)

        assert result.overall_completeness_score == pytest.approx(1.0)
        assert result.status == DQCheckStatus.PASS


class TestBusinessRulesCheck:
    """Tests for business rules validation."""

    def test_business_rules_pass(self) -> None:
        """Business rules check passes when all rules satisfied."""
        df = pl.DataFrame({"value": [100.0, 200.0, 300.0]})
        rules = [
            {
                "rule_id": "R1",
                "name": "positive_value",
                "column": "value",
                "condition": "range",
                "min": 0,
            }
        ]

        result = check_business_rules(df, rules)

        assert result.rules_passed == 1
        assert result.rules_failed == 0
        assert result.status == DQCheckStatus.PASS

    def test_business_rules_fail(self) -> None:
        """Business rules check fails when rules violated."""
        df = pl.DataFrame({"value": [-100.0, 200.0, 300.0]})
        rules = [
            {
                "rule_id": "R1",
                "name": "positive_value",
                "column": "value",
                "condition": "range",
                "min": 0,
            }
        ]

        result = check_business_rules(df, rules, contract_version="1.0.0")

        assert result.rules_failed == 1
        assert result.status == DQCheckStatus.FAIL
        assert result.rules[0].reject_reason is not None
        assert (
            result.rules[0].reject_reason.reason_code
            == "gold_semantic_business_exclusion"
        )

    def test_business_rules_not_null(self) -> None:
        """Test not_null condition."""
        df = pl.DataFrame({"id": [1, 2, None]})
        rules = [
            {
                "rule_id": "R1",
                "name": "id_required",
                "column": "id",
                "condition": "not_null",
            }
        ]

        result = check_business_rules(df, rules)

        assert result.rules_failed == 1

    def test_business_rules_in_list(self) -> None:
        """Test in_list condition."""
        df = pl.DataFrame({"status": ["active", "inactive", "unknown"]})
        rules = [
            {
                "rule_id": "R1",
                "name": "valid_status",
                "column": "status",
                "condition": "in_list",
                "values": ["active", "inactive"],
            }
        ]

        result = check_business_rules(df, rules)

        assert result.rules_failed == 1

    def test_business_rules_regex(self) -> None:
        """Test regex condition."""
        df = pl.DataFrame({"code": ["A-123", "B-456", "invalid"]})
        rules = [
            {
                "rule_id": "R1",
                "name": "code_format",
                "column": "code",
                "condition": "regex",
                "pattern": "^[A-Z]-\\d+$",
            }
        ]

        result = check_business_rules(df, rules)

        assert result.rules_failed == 1

    def test_business_rules_include_provenance_fields(self) -> None:
        """Business rules should preserve provenance and decision fields."""
        df = pl.DataFrame({"value": [-1.0, 2.0]})
        rules = [
            {
                "rule_id": "R_TRACE_01",
                "name": "non_negative",
                "column": "value",
                "condition": "range",
                "min": 0,
                "config_path": "configs/entities/chembl/activity.yaml",
                "layer": "gold",
                "field": "value",
                "severity": "error",
                "decision": "quarantine",
            }
        ]

        result = check_business_rules(df, rules)

        assert result.rules_failed == 1
        rule_result = result.rules[0]
        assert rule_result.rule_id == "R_TRACE_01"
        assert rule_result.config_path == "configs/entities/chembl/activity.yaml"
        assert rule_result.layer == "gold"
        assert rule_result.field == "value"
        assert rule_result.severity == "error"
        assert rule_result.decision == "quarantine"

    def test_business_rules_empty(self) -> None:
        """Business rules check passes when no rules specified."""
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_business_rules(df, [])

        assert result.rules_evaluated == 0
        assert result.status == DQCheckStatus.PASS

    def test_business_rules_missing_column(self) -> None:
        """Business rules check handles missing column gracefully."""
        df = pl.DataFrame({"id": [1, 2, 3]})
        rules = [{"rule_id": "R1", "column": "missing", "condition": "not_null"}]

        result = check_business_rules(df, rules)

        # Should pass since column doesn't exist
        assert result.rules_passed == 1


class TestReferentialIntegrityCheck:
    """Tests for referential integrity validation."""

    def test_referential_integrity_pass(self) -> None:
        """Referential integrity check passes when all references valid."""
        df = pl.DataFrame({"category_id": [1, 2, 1, 2]})
        ref_table = pl.DataFrame({"id": [1, 2, 3]})

        result = check_referential_integrity(
            df, {"category_id -> categories.id": ref_table}
        )

        assert result.status == DQCheckStatus.PASS

    def test_referential_integrity_fail_orphans(self) -> None:
        """Referential integrity check fails with many orphans."""
        df = pl.DataFrame({"category_id": [1, 999, 888, 777]})  # Many invalid refs
        ref_table = pl.DataFrame({"id": [1, 2, 3]})

        result = check_referential_integrity(
            df,
            {"category_id -> categories.id": ref_table},
            contract_version="1.0.0",
        )

        assert result.status == DQCheckStatus.FAIL
        fk_result = result.foreign_keys["category_id -> categories.id"]
        assert fk_result.reject_reason is not None
        assert fk_result.reject_reason.reason_code == "gold_contract_reference_failure"
        assert fk_result.reject_reason.contract_version == "1.0.0"

    def test_referential_integrity_empty_refs(self) -> None:
        """Referential integrity check passes with no references."""
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_referential_integrity(df, {})

        assert result.status == DQCheckStatus.PASS


class TestStatisticalProfileCheck:
    """Tests for statistical profile validation."""

    def test_statistical_profile_pass(self) -> None:
        """Statistical profile check passes with normal stats."""
        df = pl.DataFrame(
            {"id": [1, 2, 3, 4, 5], "value": [10.0, 20.0, 30.0, 40.0, 50.0]}
        )
        baseline_stats = {
            "null_rate_ma30": 0.0,
            "record_count_ma30": 5,
        }

        result = check_statistical_profile(df, baseline_stats)

        assert result.status == DQCheckStatus.PASS

    def test_statistical_profile_warn_high_null(self) -> None:
        """Statistical profile check warns on high null rate."""
        df = pl.DataFrame({"id": [1, 2, 3], "value": [None, None, 30.0]})
        baseline_stats = {
            "null_rate_ma30": 0.05,  # 5% baseline null rate
        }

        result = check_statistical_profile(df, baseline_stats)

        # With 2/3 nulls in value column, null rate is much higher than baseline
        assert result.status in [DQCheckStatus.WARN, DQCheckStatus.FAIL]

    def test_statistical_profile_no_baseline(self) -> None:
        """Statistical profile check passes when no baseline."""
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_statistical_profile(df, None)

        assert result.status == DQCheckStatus.PASS


class TestAnomalyDetectionCheck:
    """Tests for anomaly detection."""

    def test_anomaly_detection_cold_start(self) -> None:
        """AnomalyRecord detection in cold start mode."""
        df = pl.DataFrame({"id": [1, 2, 3]})
        baseline_stats = {"days_since_start": 10}  # Less than 30 days

        result = check_anomaly_detection(df, baseline_stats)

        assert result.cold_start_mode is True
        assert result.status == DQCheckStatus.PASS

    def test_anomaly_detection_no_baseline(self) -> None:
        """AnomalyRecord detection passes without baseline."""
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_anomaly_detection(df, None)

        assert result.cold_start_mode is True
        assert result.status == DQCheckStatus.PASS

    def test_anomaly_detection_normal(self) -> None:
        """AnomalyRecord detection passes with normal values."""
        df = pl.DataFrame(
            {"id": [1, 2, 3, 4, 5], "value": [10.0, 20.0, 30.0, 40.0, 50.0]}
        )
        baseline_stats = {
            "days_since_start": 45,
            "null_rate_ma30": 0.0,
            "record_count_ma30": 5,
        }

        result = check_anomaly_detection(df, baseline_stats)

        assert result.cold_start_mode is False
        assert result.status == DQCheckStatus.PASS


class TestSCDIntegrityCheck:
    """Tests for SCD integrity validation."""

    def test_scd_integrity_no_config(self) -> None:
        """SCD integrity check passes without config."""
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_scd_integrity(df, None)

        assert result.status == DQCheckStatus.PASS

    def test_scd_integrity_with_history(self) -> None:
        """SCD integrity check with version history."""
        df = pl.DataFrame(
            {
                "entity_id": ["A", "A", "B", "B", "C"],
                "_valid_from": [
                    datetime(2024, 1, 1),
                    datetime(2024, 6, 1),
                    datetime(2024, 1, 1),
                    datetime(2024, 3, 1),
                    datetime(2024, 1, 1),
                ],
                "_valid_to": [
                    datetime(2024, 6, 1),
                    None,
                    datetime(2024, 3, 1),
                    None,
                    None,
                ],
            }
        )
        scd_config = {
            "type": 2,
            "entity_key": "entity_id",
            "valid_from_col": "_valid_from",
            "valid_to_col": "_valid_to",
        }

        result = check_scd_integrity(df, scd_config)

        assert result.scd_type == 2
        assert result.total_entities == 3
        assert result.entities_with_history == 2


class TestDataFreshnessCheck:
    """Tests for data freshness validation."""

    def test_data_freshness_pass(self) -> None:
        """Data freshness check passes with recent data."""
        current_time = datetime(2024, 5, 15, 15, 0, tzinfo=UTC)
        df = pl.DataFrame(
            {
                "id": [1, 2],
                "_updated_at": [
                    datetime(2024, 5, 15, 14, 0, tzinfo=UTC),
                    datetime(2024, 5, 15, 14, 30, tzinfo=UTC),
                ],
            }
        )

        result = check_data_freshness(df, current_time)

        assert result.freshness_lag_hours < 24
        assert result.status == DQCheckStatus.PASS

    def test_data_freshness_warn(self) -> None:
        """Data freshness check warns on stale data."""
        current_time = datetime(2024, 5, 17, 15, 0, tzinfo=UTC)
        df = pl.DataFrame(
            {
                "id": [1, 2],
                "_updated_at": [
                    datetime(2024, 5, 15, 10, 0, tzinfo=UTC),
                    datetime(2024, 5, 15, 11, 0, tzinfo=UTC),
                ],
            }
        )

        result = check_data_freshness(df, current_time)

        # ~52 hours old
        assert result.freshness_lag_hours > 24
        assert result.status == DQCheckStatus.WARN

    def test_data_freshness_no_timestamp(self) -> None:
        """Data freshness check passes without timestamp column."""
        current_time = datetime(2024, 5, 15, 15, 0, tzinfo=UTC)
        df = pl.DataFrame({"id": [1, 2]})

        result = check_data_freshness(df, current_time)

        assert result.status == DQCheckStatus.PASS
        assert result.max_updated_at is None


class TestAnalyzeIntegration:
    """Integration tests for analyze method."""

    def test_analyze_polars_dataframe(
        self,
        gold_analyzer: GoldDQAnalyzer,
        sample_dataframe: pl.DataFrame,
        mock_config: MagicMock,
    ) -> None:
        """Analyze Polars DataFrame."""
        timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        report = gold_analyzer.analyze(
            data=sample_dataframe,
            run_id="test-run-123",
            pipeline="test_pipeline",
            target_table="gold/test/entity",
            config=mock_config,
            timestamp=timestamp,
            required_fields=["id", "name"],
        )

        assert report.layer == MedallionLayer.GOLD
        assert report.run_id == "test-run-123"
        assert report.pipeline == "test_pipeline"
        assert report.target_table == "gold/test/entity"
        assert report.summary is not None

    def test_analyze_pyarrow_table(
        self, gold_analyzer: GoldDQAnalyzer, mock_config: MagicMock
    ) -> None:
        """Analyze PyArrow Table (should be converted to Polars)."""
        table = pa.table({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        report = gold_analyzer.analyze(
            data=table,
            run_id="test-run-arrow",
            pipeline="test_pipeline",
            target_table="gold/test/entity",
            config=mock_config,
            timestamp=timestamp,
        )

        assert report.layer == MedallionLayer.GOLD
        assert report.summary is not None

    def test_analyze_overall_status_fail(
        self, gold_analyzer: GoldDQAnalyzer, mock_config: MagicMock
    ) -> None:
        """Overall status is FAIL when any check fails."""
        # DataFrame with all nulls in required field
        df = pl.DataFrame({"id": [None, None, None], "name": ["a", "b", "c"]})
        timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        report = gold_analyzer.analyze(
            data=df,
            run_id="test-run-fail",
            pipeline="test_pipeline",
            target_table="gold/test/entity",
            config=mock_config,
            timestamp=timestamp,
            required_fields=["id"],  # Will fail completeness
            completeness_threshold=0.9,
        )

        assert report.summary.failed > 0
        assert report.summary.overall_status == DQReportStatus.FAIL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
