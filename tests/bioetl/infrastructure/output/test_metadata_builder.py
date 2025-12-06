"""
Tests for MetadataBuilder.
"""
# pylint: disable=redefined-outer-name
from datetime import datetime, timezone
from pathlib import Path
import pytest

from bioetl.domain.models import RunContext
from bioetl.infrastructure.output.contracts import WriteResult
from bioetl.infrastructure.output.metadata import (
    build_dry_run_metadata,
    build_run_metadata,
)


@pytest.fixture
def run_context():
    """Fixture for RunContext."""
    return RunContext(
        run_id="test-run-123",
        entity_name="test_entity",
        provider="chembl",
        started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        metadata={"extra_key": "extra_value"}
    )


def test_build_metadata(run_context):
    """Test building metadata from WriteResult."""
    write_result = WriteResult(
        path=Path("/tmp/out/test.csv"),
        row_count=100,
        duration_sec=1.5,
        checksum="abc123hash"
    )

    qc_artifacts = [
        Path("/tmp/out/quality_report_table.csv"),
        Path("/tmp/out/correlation_report_table.csv"),
    ]
    qc_checksums = {
        "quality_report_table.csv": "qc1",
        "correlation_report_table.csv": "qc2",
    }

    meta = build_run_metadata(
        run_context,
        write_result,
        qc_artifacts=qc_artifacts,
        qc_checksums=qc_checksums,
    )

    assert meta["run_id"] == "test-run-123"
    assert meta["entity"] == "test_entity"
    assert meta["provider"] == "chembl"
    assert meta["timestamp"] == "2023-01-01T12:00:00+00:00"
    assert meta["row_count"] == 100
    assert meta["checksum"] == "abc123hash"
    assert meta["files"] == [
        "correlation_report_table.csv",
        "quality_report_table.csv",
        "test.csv",
    ]
    assert meta["checksums"]["test.csv"] == "abc123hash"
    assert meta["checksums"]["quality_report_table.csv"] == "qc1"
    assert meta["qc_artifacts"]["quality_report_table.csv"]["checksum"] == "qc1"
    assert meta["extra_key"] == "extra_value"


def test_build_dry_run_metadata(run_context):
    """Test building metadata for dry run."""
    meta = build_dry_run_metadata(run_context, row_count=50)

    assert meta["run_id"] == "test-run-123"
    assert meta["entity"] == "test_entity"
    assert meta["provider"] == "chembl"
    assert meta["timestamp"] == "2023-01-01T12:00:00+00:00"
    assert meta["row_count"] == 50
    assert meta["dry_run"] is True
    assert meta["extra_key"] == "extra_value"
    assert "checksum" not in meta
    assert "files" not in meta
