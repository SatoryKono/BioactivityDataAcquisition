"""Tests for QcArtifactWriter component."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.infrastructure.output.components.qc_artifact_writer import QcArtifactWriter


@pytest.fixture
def mock_atomic_op():
    """Create mock AtomicFileOperation."""
    op = MagicMock()

    def side_effect(path, write_fn):
        write_fn(path)

    op.write_atomic.side_effect = side_effect
    return op


@pytest.fixture
def writer(mock_atomic_op):
    """Create QcArtifactWriter with mock atomic operation."""
    return QcArtifactWriter(atomic_op=mock_atomic_op)


def test_write_qc_csv_returns_path(writer, tmp_path):
    """Test that write_qc_csv returns the path."""
    df = pd.DataFrame({"a": [1, 2, 3]})
    path = tmp_path / "report.csv"

    result = writer.write_qc_csv(df, path)

    assert result == path


def test_write_qc_csv_creates_parent_dirs(writer, tmp_path):
    """Test that parent directories are created."""
    df = pd.DataFrame({"a": [1]})
    path = tmp_path / "nested" / "dir" / "report.csv"

    writer.write_qc_csv(df, path)

    assert path.parent.exists()


def test_write_qc_csv_uses_atomic_operation(mock_atomic_op, tmp_path):
    """Test that atomic operation is used."""
    writer = QcArtifactWriter(atomic_op=mock_atomic_op)
    df = pd.DataFrame({"a": [1]})
    path = tmp_path / "report.csv"

    writer.write_qc_csv(df, path)

    mock_atomic_op.write_atomic.assert_called_once()


def test_write_qc_csv_writes_valid_csv(writer, tmp_path):
    """Test that valid CSV is written."""
    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    path = tmp_path / "report.csv"

    writer.write_qc_csv(df, path)

    # Read back and verify
    result = pd.read_csv(path)
    assert list(result.columns) == ["col1", "col2"]
    assert len(result) == 2


def test_write_qc_csv_no_index(writer, tmp_path):
    """Test that index is not written."""
    df = pd.DataFrame({"a": [1, 2, 3]})
    df.index = ["x", "y", "z"]
    path = tmp_path / "report.csv"

    writer.write_qc_csv(df, path)

    result = pd.read_csv(path)
    assert "Unnamed: 0" not in result.columns


def test_default_atomic_operation():
    """Test that default AtomicFileOperation is created."""
    writer = QcArtifactWriter()
    assert writer._atomic_op is not None
