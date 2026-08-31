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
"""Unit tests for Bronze DQ analyzer."""

from dataclasses import dataclass
from datetime import datetime, UTC

import orjson
import pytest

from bioetl.application.services.dq import BronzeDQAnalyzer
from bioetl.domain.value_objects.dq_report import (
    BronzeDQCheckType,
    DQCheckStatus,
    DQReportStatus,
    MedallionLayer,
)


pytestmark = [pytest.mark.unit, pytest.mark.timeout(90)]


@dataclass(frozen=True)
class _BronzeDQConfig:
    """Port-shaped test input without importing the infrastructure DTO."""

    checks: list[str]

    def get_checks_enums(self) -> list[BronzeDQCheckType]:
        return [
            check_type
            for check in self.checks
            if (check_type := _as_bronze_check_type(check)) is not None
        ]


def _as_bronze_check_type(value: str) -> BronzeDQCheckType | None:
    try:
        return BronzeDQCheckType(value)
    except ValueError:
        return None


class TestBronzeDQAnalyzer:
    """Tests for BronzeDQAnalyzer."""

    def test_analyze_basic_records(self) -> None:
        """Test analysis of basic JSON records."""
        analyzer = BronzeDQAnalyzer()
        config = _BronzeDQConfig(
            checks=[
                BronzeDQCheckType.RECORD_COUNT.value,
                BronzeDQCheckType.FILE_INTEGRITY.value,
                BronzeDQCheckType.SCHEMA_SNAPSHOT.value,
            ],
        )

        # Create test records
        records = [
            orjson.dumps({"id": 1, "name": "test1", "value": 100}),
            orjson.dumps({"id": 2, "name": "test2", "value": 200}),
            orjson.dumps({"id": 3, "name": "test3", "value": None}),
        ]

        timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        report = analyzer.analyze(
            records=iter(records),
            run_id="test-run-123",
            pipeline="test_pipeline",
            batch_id="batch-001",
            source_file="bronze/v1/test/entity/2025-01-15/batch_001.jsonl.zst",
            config=config,
            timestamp=timestamp,
        )

        # Verify report structure
        assert report.layer == MedallionLayer.BRONZE
        assert report.run_id == "test-run-123"
        assert report.pipeline == "test_pipeline"
        assert report.batch_id == "batch-001"

        # Verify checks
        assert "record_count" in report.checks
        assert report.checks["record_count"]["value"] == 3
        assert report.checks["record_count"]["status"] == DQCheckStatus.PASS.value

        assert "file_integrity" in report.checks
        assert "checksum_blake2" in report.checks["file_integrity"]
        assert report.checks["file_integrity"]["size_bytes"] > 0

        assert "schema_snapshot" in report.checks
        assert report.checks["schema_snapshot"]["fields_detected"] == 3
        assert "id" in report.checks["schema_snapshot"]["schema"]

        # Verify summary
        assert report.summary.total_checks == 3
        assert report.summary.overall_status == DQReportStatus.PASS

    def test_analyze_empty_records(self) -> None:
        """Test analysis with empty records."""
        analyzer = BronzeDQAnalyzer()
        config = _BronzeDQConfig(
            checks=[BronzeDQCheckType.RECORD_COUNT.value],
        )

        timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        report = analyzer.analyze(
            records=iter([]),
            run_id="test-run-empty",
            pipeline="test_pipeline",
            batch_id="batch-empty",
            source_file="bronze/v1/test/entity/2025-01-15/batch_empty.jsonl.zst",
            config=config,
            timestamp=timestamp,
        )

        assert report.checks["record_count"]["value"] == 0
        assert report.checks["record_count"]["status"] == DQCheckStatus.WARN.value

    def test_analyze_encoding_validation(self) -> None:
        """Test encoding validation check."""
        analyzer = BronzeDQAnalyzer()
        config = _BronzeDQConfig(
            checks=[BronzeDQCheckType.ENCODING_VALIDATION.value],
        )

        # Create valid UTF-8 records
        records = [
            b'{"name": "test"}',
            b'{"name": "test2"}',
        ]

        timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        report = analyzer.analyze(
            records=iter(records),
            run_id="test-run-enc",
            pipeline="test_pipeline",
            batch_id="batch-enc",
            source_file="bronze/v1/test/entity/2025-01-15/batch_enc.jsonl.zst",
            config=config,
            timestamp=timestamp,
        )

        assert "encoding_validation" in report.checks
        assert report.checks["encoding_validation"]["encoding_errors"] == 0
        assert (
            report.checks["encoding_validation"]["status"] == DQCheckStatus.PASS.value
        )

    def test_analyze_field_presence(self) -> None:
        """Test field presence check."""
        analyzer = BronzeDQAnalyzer()
        config = _BronzeDQConfig(
            checks=[BronzeDQCheckType.RAW_FIELD_PRESENCE.value],
        )

        records = [
            orjson.dumps({"id": 1, "name": "test1", "optional": "yes"}),
            orjson.dumps({"id": 2, "name": "test2"}),  # Missing optional
        ]

        timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        report = analyzer.analyze(
            records=iter(records),
            run_id="test-run-fp",
            pipeline="test_pipeline",
            batch_id="batch-fp",
            source_file="bronze/v1/test/entity/2025-01-15/batch_fp.jsonl.zst",
            config=config,
            timestamp=timestamp,
        )

        assert "raw_field_presence" in report.checks
        assert report.checks["raw_field_presence"]["id"] == pytest.approx(1.0)
        assert report.checks["raw_field_presence"]["name"] == pytest.approx(1.0)
        assert report.checks["raw_field_presence"]["optional"] == pytest.approx(0.5)

    def test_schema_and_presence_ignore_malformed_or_non_object_records(self) -> None:
        """Malformed JSON and non-object payloads must not pollute field evidence."""
        analyzer = BronzeDQAnalyzer()
        records = [b"{malformed", b"[]", orjson.dumps({"id": 1})]

        schema = analyzer._check_schema_snapshot(records)
        presence = analyzer._check_field_presence(records)

        assert schema.fields_detected == 1
        assert schema.schema == {"id": "integer"}
        assert presence == {"id": pytest.approx(1 / 3, abs=0.0001)}

    def test_field_presence_empty_batch_is_empty(self) -> None:
        """An empty Bronze batch has no field-presence ratios."""
        assert BronzeDQAnalyzer()._check_field_presence([]) == {}

    def test_encoding_check_reports_invalid_record_indexes(self) -> None:
        """Invalid UTF-8 bytes are counted and retain their input positions."""
        result = BronzeDQAnalyzer()._check_encoding([b"valid", b"\xff", b"also-valid"])

        assert result.encoding_errors == 1
        assert result.invalid_utf8_records == (1,)
        assert result.status == DQCheckStatus.FAIL

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, "null"),
            (True, "boolean"),
            (1, "integer"),
            (1.5, "float"),
            ("text", "string"),
            ([], "array"),
            ({}, "object"),
            (object(), "unknown"),
        ],
    )
    def test_infer_type_covers_json_types_and_unknown_values(
        self,
        value: object,
        expected: str,
    ) -> None:
        """Type inference distinguishes every JSON kind and safe fallback."""
        assert BronzeDQAnalyzer()._infer_type(value) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
