# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Extended unit tests for DQReportSerializer."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.medallion import Layer as MedallionLayer
from bioetl.domain.behavior.dq_serializer import DQReportSerializer, to_dict
from bioetl.domain.value_objects.dq_report import (
    BronzeDQReport,
    DQCheckStatus,
    DQReportFormat,
    DQReportStatus,
    DQReportSummary,
    DQThresholds,
    GoldDQReport,
    SilverDQReport,
)


# ============================================================================
# Shared fixtures
# ============================================================================


def _make_summary(
    status: DQReportStatus = DQReportStatus.PASS,
) -> DQReportSummary:
    return DQReportSummary(
        total_checks=3,
        passed=3,
        failed=0,
        warnings=0,
        overall_status=status,
    )


def _make_thresholds(
    status: DQCheckStatus = DQCheckStatus.PASS,
) -> DQThresholds:
    return DQThresholds(
        soft_fail_threshold=0.05,
        hard_fail_threshold=0.20,
        current_error_rate=0.01,
        threshold_status=status,
    )


def _make_bronze_report() -> BronzeDQReport:
    return BronzeDQReport(
        layer=MedallionLayer.BRONZE,
        timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        run_id="run-001",
        pipeline="chembl_activity",
        batch_id="batch-001",
        source_file="chembl/activity/2024-01-15/batch001.jsonl.zst",
        checks={"record_count": {"status": "pass", "value": 1000}},
        summary=_make_summary(),
    )


def _make_silver_report(
    summary: DQReportSummary | None = None,
) -> SilverDQReport:
    return SilverDQReport(
        layer=MedallionLayer.SILVER,
        timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        run_id="run-001",
        pipeline="chembl_activity",
        source_batch_ids=("batch-001", "batch-002"),
        target_table="silver/chembl/activity",
        checks={"null_rate": {"status": "warn", "rate": 0.07}},
        thresholds=_make_thresholds(),
        summary=summary or _make_summary(DQReportStatus.WARNING),
    )


def _make_gold_report() -> GoldDQReport:
    return GoldDQReport(
        layer=MedallionLayer.GOLD,
        timestamp=datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC),
        run_id="run-001",
        pipeline="chembl_activity",
        target_table="gold/chembl/activity",
        checks={},
        data_freshness=None,
        summary=_make_summary(),
    )


# ============================================================================
# Tests for to_dict (standalone function)
# ============================================================================


@pytest.mark.unit
class TestToDictFunction:
    """Tests for the to_dict standalone function."""

    def test_dict_input_is_returned(self) -> None:
        """Test that dict input is returned as-is after serialization."""
        result = to_dict({"key": "value"})
        assert result == {"key": "value"}

    def test_primitive_wrapped_in_value_key(self) -> None:
        """Test that primitive is wrapped in {'value': ...}."""
        assert to_dict(42) == {"value": 42}
        assert to_dict("hello") == {"value": "hello"}
        assert to_dict(None) == {"value": None}


# ============================================================================
# Tests for DQReportSerializer
# ============================================================================


@pytest.mark.unit
class TestDQReportSerializerToDict:
    """Tests for DQReportSerializer.to_dict() method."""

    def test_bronze_report_to_dict(self) -> None:
        """Test serializing BronzeDQReport to dict."""
        serializer = DQReportSerializer()
        report = _make_bronze_report()
        result = serializer.to_dict(report)
        assert isinstance(result, dict)
        assert "run_id" in result
        assert result["run_id"] == "run-001"

    def test_silver_report_to_dict(self) -> None:
        """Test serializing SilverDQReport to dict."""
        serializer = DQReportSerializer()
        report = _make_silver_report()
        result = serializer.to_dict(report)
        assert isinstance(result, dict)
        assert "pipeline" in result


@pytest.mark.unit
class TestDQReportSerializerJSON:
    """Tests for DQReportSerializer JSON serialization."""

    def test_serialize_bronze_as_json(self) -> None:
        """Test serializing BronzeDQReport to JSON."""
        serializer = DQReportSerializer()
        report = _make_bronze_report()
        result = serializer.serialize(report, format=DQReportFormat.JSON)
        assert isinstance(result, str)
        assert "run-001" in result
        assert "chembl_activity" in result

    def test_serialize_silver_as_json(self) -> None:
        """Test serializing SilverDQReport to JSON."""
        serializer = DQReportSerializer()
        report = _make_silver_report()
        result = serializer.serialize(report, format=DQReportFormat.JSON)
        assert isinstance(result, str)
        assert "silver" in result.lower() or "run-001" in result

    def test_serialize_gold_as_json(self) -> None:
        """Test serializing GoldDQReport to JSON."""
        serializer = DQReportSerializer()
        report = _make_gold_report()
        result = serializer.serialize(report, format=DQReportFormat.JSON)
        assert isinstance(result, str)
        assert "run-001" in result

    def test_default_format_is_json(self) -> None:
        """Test that default serialize format is JSON."""
        serializer = DQReportSerializer()
        report = _make_bronze_report()
        result = serializer.serialize(report)
        # JSON should start with { and end with }
        stripped = result.strip()
        assert stripped.startswith("{") or stripped.startswith("[")


@pytest.mark.unit
class TestDQReportSerializerYAML:
    """Tests for DQReportSerializer YAML serialization."""

    def test_serialize_bronze_as_yaml(self) -> None:
        """Test serializing BronzeDQReport to YAML."""
        serializer = DQReportSerializer()
        report = _make_bronze_report()
        result = serializer.serialize(report, format=DQReportFormat.YAML)
        assert isinstance(result, str)
        assert len(result) > 0
        # YAML format should contain key: value patterns
        assert ":" in result

    def test_serialize_silver_as_yaml(self) -> None:
        """Test serializing SilverDQReport to YAML."""
        serializer = DQReportSerializer()
        report = _make_silver_report()
        result = serializer.serialize(report, format=DQReportFormat.YAML)
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.unit
class TestDQReportSerializerHTML:
    """Tests for DQReportSerializer HTML serialization."""

    def test_serialize_bronze_as_html(self) -> None:
        """Test serializing BronzeDQReport to HTML."""
        serializer = DQReportSerializer()
        report = _make_bronze_report()
        result = serializer.serialize(report, format=DQReportFormat.HTML)
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result
        assert "BRONZE" in result

    def test_serialize_silver_as_html(self) -> None:
        """Test serializing SilverDQReport to HTML."""
        serializer = DQReportSerializer()
        report = _make_silver_report()
        result = serializer.serialize(report, format=DQReportFormat.HTML)
        assert "<!DOCTYPE html>" in result
        assert "SILVER" in result

    def test_html_contains_run_id(self) -> None:
        """Test HTML report contains run_id."""
        serializer = DQReportSerializer()
        report = _make_bronze_report()
        result = serializer.serialize(report, format=DQReportFormat.HTML)
        assert "run-001" in result

    def test_html_contains_pipeline_name(self) -> None:
        """Test HTML report contains pipeline name."""
        serializer = DQReportSerializer()
        report = _make_bronze_report()
        result = serializer.serialize(report, format=DQReportFormat.HTML)
        assert "chembl_activity" in result

    def test_html_contains_summary_counts(self) -> None:
        """Test HTML report contains summary counts."""
        serializer = DQReportSerializer()
        report = _make_bronze_report()
        result = serializer.serialize(report, format=DQReportFormat.HTML)
        assert "Total Checks" in result

    def test_html_with_warning_status(self) -> None:
        """Test HTML report with WARNING status shows appropriate badge."""
        serializer = DQReportSerializer()
        report = _make_silver_report(summary=_make_summary(DQReportStatus.WARNING))
        result = serializer.serialize(report, format=DQReportFormat.HTML)
        assert "warning" in result.lower()

    def test_html_with_checks_rendered(self) -> None:
        """Test HTML renders checks section."""
        serializer = DQReportSerializer()
        report = _make_bronze_report()
        result = serializer.serialize(report, format=DQReportFormat.HTML)
        assert "Check Results" in result

    def test_html_with_thresholds_rendered(self) -> None:
        """Test HTML renders thresholds when present (SilverDQReport)."""
        serializer = DQReportSerializer()
        report = _make_silver_report()
        result = serializer.serialize(report, format=DQReportFormat.HTML)
        assert "DQ Thresholds" in result or "Threshold" in result


@pytest.mark.unit
class TestDQReportSerializerInternals:
    """Tests for DQReportSerializer internal helper methods."""

    def test_status_color_pass(self) -> None:
        """Test _status_color returns 'pass' for pass status."""
        serializer = DQReportSerializer()
        assert serializer._status_color("pass") == "pass"
        assert serializer._status_color("passed") == "pass"

    def test_status_color_warn(self) -> None:
        """Test _status_color returns 'warning' for warn status."""
        serializer = DQReportSerializer()
        assert serializer._status_color("warn") == "warning"
        assert serializer._status_color("warning") == "warning"

    def test_status_color_fail(self) -> None:
        """Test _status_color returns 'fail' for unknown status."""
        serializer = DQReportSerializer()
        assert serializer._status_color("fail") == "fail"
        assert serializer._status_color("FAILED") == "fail"
        assert serializer._status_color("error") == "fail"

    def test_yaml_value_none(self) -> None:
        """Test _yaml_value serializes None as 'null'."""
        serializer = DQReportSerializer()
        assert serializer._yaml_value(None) == "null"

    def test_yaml_value_bool_true(self) -> None:
        """Test _yaml_value serializes True as 'true'."""
        serializer = DQReportSerializer()
        assert serializer._yaml_value(True) == "true"

    def test_yaml_value_bool_false(self) -> None:
        """Test _yaml_value serializes False as 'false'."""
        serializer = DQReportSerializer()
        assert serializer._yaml_value(False) == "false"

    def test_yaml_value_string(self) -> None:
        """Test _yaml_value serializes plain string."""
        serializer = DQReportSerializer()
        result = serializer._yaml_value("hello")
        assert result == "hello"

    def test_yaml_value_string_with_special_chars(self) -> None:
        """Test _yaml_value quotes strings with special YAML chars."""
        serializer = DQReportSerializer()
        # Colon should trigger quoting
        result = serializer._yaml_value("key: value")
        assert result.startswith('"') and result.endswith('"')

    def test_yaml_value_string_with_newline(self) -> None:
        """Test _yaml_value quotes strings with newlines."""
        serializer = DQReportSerializer()
        result = serializer._yaml_value("line1\nline2")
        assert result.startswith('"')

    def test_yaml_value_string_with_hash(self) -> None:
        """Test _yaml_value quotes strings with hash characters."""
        serializer = DQReportSerializer()
        result = serializer._yaml_value("value # comment")
        assert result.startswith('"')

    def test_yaml_value_number(self) -> None:
        """Test _yaml_value serializes numbers."""
        serializer = DQReportSerializer()
        assert serializer._yaml_value(42) == "42"
        assert serializer._yaml_value(3.14) == "3.14"

    def test_render_checks_html_empty(self) -> None:
        """Test _render_checks_html with empty checks."""
        serializer = DQReportSerializer()
        result = serializer._render_checks_html({})
        assert "No checks performed" in result

    def test_render_checks_html_with_dict_check(self) -> None:
        """Test _render_checks_html renders dict-type checks."""
        serializer = DQReportSerializer()
        checks = {"record_count": {"status": "pass", "value": 1000}}
        result = serializer._render_checks_html(checks)
        assert "record_count" in result.lower() or "Record Count" in result

    def test_render_checks_html_with_non_dict_check(self) -> None:
        """Test _render_checks_html renders non-dict checks."""
        serializer = DQReportSerializer()
        checks = {"simple_check": "ok"}
        result = serializer._render_checks_html(checks)
        assert "ok" in result

    def test_render_check_details_with_status_only(self) -> None:
        """Test _render_check_details with only status key."""
        serializer = DQReportSerializer()
        result = serializer._render_check_details({"status": "pass"})
        assert "No details available" in result

    def test_render_check_details_with_data(self) -> None:
        """Test _render_check_details renders detail rows."""
        serializer = DQReportSerializer()
        result = serializer._render_check_details(
            {
                "status": "pass",
                "value": 1000,
                "threshold": 500,
            }
        )
        assert "<table>" in result
        assert "value" in result.lower() or "Value" in result

    def test_format_detail_value_dict(self) -> None:
        """Test _format_detail_value with dict shows pre block."""
        serializer = DQReportSerializer()
        result = serializer._format_detail_value({"key": "val"})
        assert "<pre>" in result

    def test_format_detail_value_list(self) -> None:
        """Test _format_detail_value with list shows comma-separated."""
        serializer = DQReportSerializer()
        result = serializer._format_detail_value(["a", "b", "c"])
        assert "a" in result and "b" in result

    def test_format_detail_value_empty_list(self) -> None:
        """Test _format_detail_value with empty list."""
        serializer = DQReportSerializer()
        result = serializer._format_detail_value([])
        assert result == "[]"

    def test_format_detail_value_tuple(self) -> None:
        """Test _format_detail_value with tuple shows comma-separated."""
        serializer = DQReportSerializer()
        result = serializer._format_detail_value(("x", "y"))
        assert "x" in result

    def test_render_thresholds_html_empty(self) -> None:
        """Test _render_thresholds_html with empty dict returns empty string."""
        serializer = DQReportSerializer()
        result = serializer._render_thresholds_html({})
        assert result == ""

    def test_render_thresholds_html_with_data(self) -> None:
        """Test _render_thresholds_html renders threshold data."""
        serializer = DQReportSerializer()
        thresholds = {
            "threshold_status": "pass",
            "soft_fail_threshold": 0.05,
            "hard_fail_threshold": 0.20,
            "current_error_rate": 0.01,
        }
        result = serializer._render_thresholds_html(thresholds)
        assert "DQ Thresholds" in result
        assert "0.05" in result
