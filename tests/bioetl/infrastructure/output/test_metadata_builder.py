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
    build_base_metadata,
    build_dry_run_metadata,
    build_run_metadata,
)


def test_build_metadata(run_context_factory):
    """Test building metadata from WriteResult."""
    run_context = run_context_factory(
        run_id="test-run-123",
        started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        metadata={"extra_key": "extra_value"},
    )
    write_result = WriteResult(
        path=Path("/tmp/out/test.csv"),
        row_count=100,
        duration_sec=1.5,
        checksum="abc123hash",
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

    _assert_metadata(meta, write_result, run_context)
    _assert_checksums(meta)


def test_build_dry_run_metadata(run_context_factory):
    """Test building metadata for dry run."""
    run_context = run_context_factory(
        run_id="test-run-123",
        started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        metadata={"extra_key": "extra_value"},
    )
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


def test_run_and_dry_run_share_base_fields(run_context):
    """Run и dry-run должны совпадать по базовым полям и различаться по специфике."""
    write_result = WriteResult(
        path=Path("/tmp/out/test.csv"),
        row_count=42,
        duration_sec=1.0,
        checksum="run-hash",
    )

    run_meta = build_run_metadata(run_context, write_result)
    dry_run_meta = build_dry_run_metadata(run_context, row_count=42)

    base_run_meta = build_base_metadata(run_context, row_count=42)

    _assert_common_metadata_fields(run_meta, base_run_meta)
    _assert_common_metadata_fields(dry_run_meta, base_run_meta)

    assert "checksum" in run_meta
    assert "files" in run_meta
    assert "dry_run" not in run_meta

    assert dry_run_meta["dry_run"] is True
    assert "checksum" not in dry_run_meta
    assert "files" not in dry_run_meta


def _assert_metadata(
    meta: dict, write_result: WriteResult, run_context: RunContext
) -> None:
    assert meta["run_id"] == run_context.run_id
    assert meta["entity"] == run_context.entity_name
    assert meta["provider"] == run_context.provider
    assert meta["timestamp"] == run_context.started_at.isoformat()
    assert meta["row_count"] == write_result.row_count
    assert meta["checksum"] == write_result.checksum
    assert meta["files"] == [
        "correlation_report_table.csv",
        "quality_report_table.csv",
        "test.csv",
    ]
    assert meta["extra_key"] == "extra_value"


def _assert_checksums(meta: dict) -> None:
    assert meta["checksums"]["test.csv"] == "abc123hash"
    assert meta["checksums"]["quality_report_table.csv"] == "qc1"
    assert meta["qc_artifacts"]["quality_report_table.csv"]["checksum"] == "qc1"


def _assert_common_metadata_fields(meta: dict, expected: dict) -> None:
    for key, value in expected.items():
        assert meta[key] == value
