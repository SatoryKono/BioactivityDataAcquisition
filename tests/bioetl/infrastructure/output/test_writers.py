"""
Tests for concrete writer implementations.
"""
# pylint: disable=redefined-outer-name
import hashlib
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
import yaml

from bioetl.infrastructure.output.impl.base_writer import BaseWriterImpl
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl
from bioetl.infrastructure.output.impl.metadata_writer import (
    MetadataWriterImpl,
)
from bioetl.infrastructure.output.impl.parquet_writer import ParquetWriterImpl


class DummyWriter(BaseWriterImpl):
    """Minimal writer for base class tests."""

    def __init__(
        self, *, checksum_fn: Callable[[Path], str] | None = None
    ) -> None:
        super().__init__(atomic=False, checksum_fn=checksum_fn)

    def _write_frame(self, df: pd.DataFrame, path: Path) -> None:
        df.to_csv(path, index=False)

    def supports_format(self, fmt: str) -> bool:  # pragma: no cover - not used
        return fmt.lower() == "dummy"


@pytest.fixture
def csv_writer():
    """Fixture for CSV writer."""
    return CsvWriterImpl()


@pytest.fixture
def parquet_writer():
    """Fixture for Parquet writer."""
    return ParquetWriterImpl()


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


def test_csv_writer_column_order_and_fill(csv_writer, tmp_path):
    """CSV writer should reorder columns and fill missing ones with None."""
    df = pd.DataFrame({"b": [1], "a": [2]})
    path = tmp_path / "ordered.csv"

    result = csv_writer.write(df, path, column_order=["a", "b", "c"])

    assert result.row_count == 1
    df_read = pd.read_csv(path)
    assert list(df_read.columns) == ["a", "b", "c"]
    assert df_read.loc[0, "a"] == 2
    assert df_read.loc[0, "b"] == 1
    assert pd.isna(df_read.loc[0, "c"])


def test_csv_writer_properties(csv_writer):
    """Test CSV writer properties."""
    assert not csv_writer.atomic
    assert csv_writer.supports_format("csv")
    assert csv_writer.supports_format("CSV")
    assert not csv_writer.supports_format("parquet")


def test_parquet_writer_column_order_and_fill(parquet_writer, tmp_path):
    """Parquet writer should reorder columns and fill missing ones with None."""
    pytest.importorskip("pyarrow")
    df = pd.DataFrame({"x": ["foo"], "y": ["bar"]})
    path = tmp_path / "ordered.parquet"

    result = parquet_writer.write(df, path, column_order=["y", "x", "z"])

    assert parquet_writer.atomic
    assert result.row_count == 1
    assert result.checksum is None
    df_read = pd.read_parquet(path)
    assert list(df_read.columns) == ["y", "x", "z"]
    assert df_read.loc[0, "y"] == "bar"
    assert df_read.loc[0, "x"] == "foo"
    assert pd.isna(df_read.loc[0, "z"])


def test_writer_uses_checksum_fn(tmp_path):
    """Base writer should delegate checksum when provided."""
    checksum_fn = MagicMock(return_value="abc123")
    writer = DummyWriter(checksum_fn=checksum_fn)
    df = pd.DataFrame({"a": [1]})
    path = tmp_path / "dummy.csv"

    result = writer.write(df, path)

    checksum_fn.assert_called_once_with(path)
    assert result.checksum == "abc123"
    assert result.row_count == 1
    assert list(pd.read_csv(path).columns) == ["a"]


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
