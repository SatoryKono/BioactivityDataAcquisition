"""
Tests for concrete writer implementations.
"""
# pylint: disable=redefined-outer-name
import hashlib

import pandas as pd
import pytest
import yaml

from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl
from bioetl.infrastructure.output.impl.metadata_writer import (
    MetadataWriterImpl,
)


@pytest.fixture
def csv_writer():
    """Fixture for CSV writer."""
    return CsvWriterImpl()


@pytest.fixture
def metadata_writer():
    """Fixture for Metadata writer."""
    return MetadataWriterImpl()


def test_csv_writer_write(csv_writer, tmp_path):
    """Test basic CSV writing."""
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    path = tmp_path / "test.csv"

    result = csv_writer.write(df, path)

    assert path.exists()
    assert result.path == path
    assert result.row_count == 2
    assert result.duration_sec > 0
    assert result.checksum is not None

    # Verify content
    df_read = pd.read_csv(path)
    pd.testing.assert_frame_equal(df, df_read)


def test_csv_writer_properties(csv_writer):
    """Test CSV writer properties."""
    assert not csv_writer.atomic
    assert csv_writer.supports_format("csv")
    assert csv_writer.supports_format("CSV")
    assert not csv_writer.supports_format("parquet")


def test_metadata_writer_write_meta(metadata_writer, tmp_path):
    """Test writing metadata to YAML."""
    meta = {"key": "value", "nested": {"k": "v"}}
    path = tmp_path / "meta.yaml"

    metadata_writer.write_meta(meta, path)

    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    assert loaded == meta


def test_metadata_writer_write_qc_report(metadata_writer, tmp_path):
    """Test writing QC report."""
    df = pd.DataFrame({"a": [1, None], "b": ["x", "x"]})
    path = tmp_path / "qc_report.csv"

    metadata_writer.write_qc_report(df, path)

    assert path.exists()
    report = pd.read_csv(path)
    assert "column" in report.columns
    assert "null_count" in report.columns
    assert "unique_count" in report.columns

    # Check specific values
    row_a = report[report["column"] == "a"].iloc[0]
    assert row_a["null_count"] == 1
    assert row_a["unique_count"] == 1


def test_metadata_writer_generate_checksums(metadata_writer, tmp_path):
    """Test checksum generation for files."""
    f1 = tmp_path / "f1.txt"
    f1.write_text("content1", encoding="utf-8")
    f2 = tmp_path / "f2.txt"
    f2.write_text("content2", encoding="utf-8")

    checksums = metadata_writer.generate_checksums([f1, f2])

    assert f1.name in checksums
    assert f2.name in checksums
    assert checksums[f1.name] == hashlib.sha256(b"content1").hexdigest()
    assert checksums[f2.name] == hashlib.sha256(b"content2").hexdigest()


def test_metadata_writer_generate_checksums_missing_file(
    metadata_writer, tmp_path
):
    """Test checksum generation skips missing files."""
    f1 = tmp_path / "exists.txt"
    f1.write_text("content", encoding="utf-8")
    f2 = tmp_path / "missing.txt"

    checksums = metadata_writer.generate_checksums([f1, f2])

    assert f1.name in checksums
    assert f2.name not in checksums
