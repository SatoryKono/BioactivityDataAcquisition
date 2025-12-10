"""Tests for MetadataBuilder component."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.domain.clients.base.output.contracts import WriteResult
from bioetl.domain.configs import QcConfig
from bioetl.infrastructure.output.components.metadata_builder import MetadataBuilder


@pytest.fixture
def builder():
    """Create MetadataBuilder instance."""
    return MetadataBuilder()


@pytest.fixture
def mock_context():
    """Create mock RunContext."""
    context = MagicMock()
    context.run_id = "test-run-123"
    context.entity_name = "test_entity"
    context.provider = "test_provider"
    context.started_at = datetime(2024, 1, 15, 10, 30, 0)
    context.metadata = {"custom_key": "custom_value"}
    context.config = {}
    return context


@pytest.fixture
def mock_write_result(tmp_path):
    """Create mock WriteResult."""
    return WriteResult(
        path=tmp_path / "output.csv",
        row_count=100,
        duration_sec=1.5,
        checksum="abc123checksum",
    )


def test_build_run_metadata_basic(builder, mock_context, mock_write_result):
    """Test basic metadata building."""
    meta = builder.build_run_metadata(mock_context, mock_write_result)

    assert meta["run_id"] == "test-run-123"
    assert meta["entity"] == "test_entity"
    assert meta["provider"] == "test_provider"
    assert meta["row_count"] == 100
    assert meta["checksum"] == "abc123checksum"
    assert meta["hash"] == "abc123checksum"  # Backward compatibility


def test_build_run_metadata_timestamp(builder, mock_context, mock_write_result):
    """Test timestamp is ISO formatted."""
    meta = builder.build_run_metadata(mock_context, mock_write_result)

    assert meta["timestamp"] == "2024-01-15T10:30:00"


def test_build_run_metadata_with_qc_artifacts(builder, mock_context, mock_write_result):
    """Test metadata with QC artifacts."""
    qc_artifacts = [
        Path("/tmp/quality_report.csv"),
        Path("/tmp/correlation_report.csv"),
    ]
    qc_checksums = {
        "quality_report.csv": "qc_checksum_1",
        "correlation_report.csv": "qc_checksum_2",
    }

    meta = builder.build_run_metadata(
        mock_context,
        mock_write_result,
        qc_artifacts=qc_artifacts,
        qc_checksums=qc_checksums,
    )

    assert "qc_artifacts" in meta
    assert "quality_report.csv" in meta["qc_artifacts"]
    assert "correlation_report.csv" in meta["qc_artifacts"]
    assert meta["qc_artifacts"]["quality_report.csv"]["checksum"] == "qc_checksum_1"


def test_build_run_metadata_files_list(builder, mock_context, mock_write_result):
    """Test files list includes data and QC artifacts."""
    qc_artifacts = [Path("/tmp/qc.csv")]

    meta = builder.build_run_metadata(
        mock_context,
        mock_write_result,
        qc_artifacts=qc_artifacts,
    )

    assert "output.csv" in meta["files"]
    assert "qc.csv" in meta["files"]
    assert meta["files"] == sorted(meta["files"])  # Should be sorted


def test_build_run_metadata_checksums_dict(builder, mock_context, mock_write_result):
    """Test checksums dictionary."""
    qc_checksums = {"qc.csv": "qc_checksum"}

    meta = builder.build_run_metadata(
        mock_context,
        mock_write_result,
        qc_artifacts=[Path("/tmp/qc.csv")],
        qc_checksums=qc_checksums,
    )

    assert meta["checksums"]["output.csv"] == "abc123checksum"
    assert meta["checksums"]["qc.csv"] == "qc_checksum"


def test_build_run_metadata_qc_config(builder, mock_context, mock_write_result):
    """Test QC config is included."""
    qc_config = QcConfig(
        enable_quality_report=True,
        enable_correlation_report=False,
        min_coverage=0.9,
    )

    meta = builder.build_run_metadata(
        mock_context,
        mock_write_result,
        qc_config=qc_config,
    )

    assert meta["qc_config"]["enable_quality_report"] is True
    assert meta["qc_config"]["enable_correlation_report"] is False
    assert meta["qc_config"]["min_coverage"] == 0.9


def test_build_run_metadata_includes_context_metadata(
    builder, mock_context, mock_write_result
):
    """Test that context metadata is merged."""
    meta = builder.build_run_metadata(mock_context, mock_write_result)

    assert meta["custom_key"] == "custom_value"


def test_build_dry_run_metadata(builder, mock_context):
    """Test dry run metadata."""
    meta = builder.build_dry_run_metadata(mock_context, row_count=50)

    assert meta["run_id"] == "test-run-123"
    assert meta["entity"] == "test_entity"
    assert meta["row_count"] == 50
    assert meta["dry_run"] is True
    assert meta["custom_key"] == "custom_value"


def test_build_dry_run_metadata_no_checksum(builder, mock_context):
    """Test dry run doesn't include checksum fields."""
    meta = builder.build_dry_run_metadata(mock_context, row_count=50)

    assert "checksum" not in meta
    assert "hash" not in meta
    assert "files" not in meta


def test_hash_version_constant(builder, mock_context, mock_write_result):
    """Test hash version is included."""
    meta = builder.build_run_metadata(mock_context, mock_write_result)

    assert meta["hash_version"] == "v1_blake2b_256"
