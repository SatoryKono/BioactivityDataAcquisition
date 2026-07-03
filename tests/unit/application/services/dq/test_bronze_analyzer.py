"""Unit tests for Bronze DQ analyzer."""

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
from bioetl.infrastructure.schemas.dq_report_config import BronzeDQReportConfig


pytestmark = pytest.mark.unit


class TestBronzeDQAnalyzer:
    """Tests for BronzeDQAnalyzer."""

    def test_analyze_basic_records(self) -> None:
        """Test analysis of basic JSON records."""
        analyzer = BronzeDQAnalyzer()
        config = BronzeDQReportConfig(
            enabled=True,
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
        config = BronzeDQReportConfig(
            enabled=True,
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
        config = BronzeDQReportConfig(
            enabled=True,
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
        config = BronzeDQReportConfig(
            enabled=True,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
