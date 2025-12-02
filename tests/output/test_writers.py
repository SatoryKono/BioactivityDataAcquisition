"""
Tests for specific writer implementations.
"""
import hashlib
from pathlib import Path

import pandas as pd
import yaml

import bioetl.infrastructure.output.impl.csv_writer as csv_writer
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriterImpl


def test_csv_writer_write(tmp_path):
    """Test CSV writer writes correct content."""
    writer = CsvWriterImpl()
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    output_path = tmp_path / "test.csv"

    result = writer.write(df, output_path)

    assert output_path.exists()
    assert result.row_count == 2
    assert result.path == output_path
    assert result.duration_sec >= 0
    assert result.checksum
    assert result.checksum == hashlib.sha256(output_path.read_bytes()).hexdigest()

    # Verify content
    read_df = pd.read_csv(output_path)
    pd.testing.assert_frame_equal(df, read_df)


def test_csv_writer_supports_format():
    """Test CSV writer format support."""
    writer = CsvWriterImpl()
    assert writer.supports_format("csv")
    assert writer.supports_format("CSV")
    assert not writer.supports_format("parquet")


def test_csv_writer_atomic_property():
    """Test CSV writer atomic property."""
    writer = CsvWriterImpl()
    assert writer.atomic is True


def test_csv_writer_atomic_write(tmp_path, monkeypatch):
    """Test CSV writer writes via temp file and replaces atomically."""
    writer = CsvWriterImpl()
    df = pd.DataFrame({"a": [1], "b": ["x"]})
    output_path = tmp_path / "data.csv"
    temp_path = output_path.with_suffix(".tmp")

    replace_calls: list[tuple[Path, Path]] = []
    real_replace = csv_writer.os.replace

    def recording_replace(src: Path, dst: Path) -> None:
        replace_calls.append((Path(src), Path(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(csv_writer.os, "replace", recording_replace)

    result = writer.write(df, output_path)

    assert replace_calls == [(temp_path, output_path)]
    assert output_path.exists()
    assert not temp_path.exists()
    pd.testing.assert_frame_equal(df, pd.read_csv(output_path))
    assert result.checksum == hashlib.sha256(output_path.read_bytes()).hexdigest()


def test_metadata_writer_write_meta(tmp_path):
    """Test metadata writer writes correct YAML."""
    writer = MetadataWriterImpl()
    meta = {"run_id": "123", "status": "success"}
    output_path = tmp_path / "meta.yaml"

    writer.write_meta(meta, output_path)

    assert output_path.exists()
    with open(output_path, "r") as f:
        loaded = yaml.safe_load(f)
    assert loaded == meta


def test_metadata_writer_write_qc_report(tmp_path):
    """Test metadata writer generates QC report."""
    writer = MetadataWriterImpl()
    df = pd.DataFrame({"a": [1, None], "b": ["x", "x"]})
    output_path = tmp_path / "qc.csv"

    writer.write_qc_report(df, output_path)

    assert output_path.exists()
    report = pd.read_csv(output_path)
    assert "column" in report.columns
    assert "null_count" in report.columns
    assert "unique_count" in report.columns

    row_a = report[report["column"] == "a"].iloc[0]
    assert row_a["null_count"] == 1
    assert row_a["unique_count"] == 1


def test_metadata_writer_generate_checksums(tmp_path):
    """Test checksum generation."""
    writer = MetadataWriterImpl()
    p1 = tmp_path / "f1.txt"
    p1.write_text("abc", encoding="utf-8")
    p2 = tmp_path / "f2.txt"
    p2.write_text("def", encoding="utf-8")

    checksums = writer.generate_checksums([p1, p2])

    assert len(checksums) == 2
    assert "f1.txt" in checksums
    assert "f2.txt" in checksums
    # known sha256 for "abc"
    # echo -n "abc" | shasum -a 256
    # ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
    expected = (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert checksums["f1.txt"] == expected
