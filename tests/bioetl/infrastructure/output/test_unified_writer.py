"""
Tests for the UnifiedOutputWriter.
"""
# pylint: disable=redefined-outer-name, protected-access
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from bioetl.domain.models import RunContext
from bioetl.infrastructure.output.contracts import WriteResult
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


@pytest.fixture
def mock_writer_fixture():
    """Fixture for mock writer."""
    return MagicMock()


@pytest.fixture
def mock_metadata_writer_fixture():
    """Fixture for mock metadata writer."""
    return MagicMock()


@pytest.fixture
def mock_config_fixture():
    """Fixture for mock configuration."""
    config = MagicMock()
    config.stable_sort = True
    return config


@pytest.fixture
def mock_atomic_op():
    """Fixture for mock atomic operation."""
    op = MagicMock()

    # Default implementation calls the callback
    def side_effect(path, write_fn):
        write_fn(path)
    op.write_atomic.side_effect = side_effect
    return op


@pytest.fixture
def unified_writer(
    mock_writer_fixture,
    mock_metadata_writer_fixture,
    mock_config_fixture,
    mock_atomic_op,
):
    """Fixture for unified writer."""
    return UnifiedOutputWriter(
        mock_writer_fixture,
        mock_metadata_writer_fixture,
        mock_config_fixture,
        atomic_op=mock_atomic_op,
    )


@pytest.fixture
def run_context():
    """Fixture for run context."""
    return RunContext(
        run_id="test-run",
        entity_name="test_entity",
        provider="chembl",
        started_at=datetime.now(timezone.utc)
    )


def test_write_result_success(
    unified_writer,
    mock_writer_fixture,
    mock_metadata_writer_fixture,
    run_context,
    tmp_path
):
    """Test successful write result handling."""
    # Arrange
    df = pd.DataFrame({"a": [1, 2]})
    output_dir = tmp_path / "out"

    # Mock writer side effect to create the file
    def create_file(df, path, **kwargs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return WriteResult(
            path=path,
            row_count=len(df),
            checksum="abc",
            duration_sec=0.1
        )

    mock_writer_fixture.write.side_effect = create_file
    
    # Patch checksum function
    with patch("bioetl.infrastructure.output.unified_writer.compute_file_sha256") as mock_checksum:
        mock_checksum.return_value = "real_checksum"

        # Act
        result = unified_writer.write_result(
            df,
            output_dir,
            "test_entity",
            run_context
        )

        # Assert
        assert result.row_count == 2
        assert result.checksum == "real_checksum"

        # Verify calls
        mock_writer_fixture.write.assert_called_once()
        mock_metadata_writer_fixture.write_meta.assert_called_once()
        mock_checksum.assert_called_once()


def test_unified_writer_delegates_atomicity(
    unified_writer,
    mock_writer_fixture,
    mock_atomic_op,
    run_context,
    tmp_path
):
    """Test that UnifiedOutputWriter delegates to AtomicFileOperation."""
    # Arrange
    df = pd.DataFrame({"a": [1]})
    output_dir = tmp_path / "out"

    mock_writer_fixture.write.return_value = WriteResult(
        path=output_dir / "test.csv",
        row_count=1,
        checksum="abc",
        duration_sec=0.1
    )
    
    with patch("bioetl.infrastructure.output.unified_writer.compute_file_sha256") as mock_checksum:
        mock_checksum.return_value = "abc"

        # Act
        unified_writer.write_result(
            df,
            output_dir,
            "test_entity",
            run_context
        )

        # Assert
        mock_atomic_op.write_atomic.assert_called_once()
        # Verify that the first argument to write_atomic is the correct path
        args, _ = mock_atomic_op.write_atomic.call_args
        assert args[0] == output_dir / "test_entity.csv"


def test_stable_sort_false(unified_writer, mock_config_fixture, run_context):
    """Test behavior when stable_sort is False."""
    mock_config_fixture.stable_sort = False
    df = pd.DataFrame({"b": [2], "a": [1]})

    result_df = unified_writer._stable_sort(df, run_context)

    # Should preserve order
    assert list(result_df.columns) == ["b", "a"]
    assert result_df.iloc[0]["b"] == 2


def test_stable_sort_columns_and_rows(
    unified_writer, mock_config_fixture, run_context
):
    """Test stable sort of columns and rows."""
    mock_config_fixture.stable_sort = True

    # Setup config with business keys
    run_context.config = {
        "hashing": {
            "business_key_fields": ["id"]
        }
    }

    df = pd.DataFrame({
        "id": [2, 1, 3],
        "b": [20, 10, 30],
        "a": [200, 100, 300]
    })

    result_df = unified_writer._stable_sort(df, run_context)

    # Columns sorted alphabetically
    assert list(result_df.columns) == ["a", "b", "id"]

    # Rows sorted by 'id'
    assert result_df["id"].tolist() == [1, 2, 3]
    assert result_df["a"].tolist() == [100, 200, 300]


def test_write_result_raises_on_no_inner_result(
    unified_writer,
    mock_writer_fixture,
    run_context,
    tmp_path
):
    """Test error raised when inner writer returns nothing."""
    # Arrange
    df = pd.DataFrame({"a": [1]})
    output_dir = tmp_path / "out"

    # inner writer returns None (mock default)
    mock_writer_fixture.write.return_value = None

    # Act & Assert
    with pytest.raises(
        RuntimeError, match="Inner writer did not return result"
    ):
        unified_writer.write_result(
            df,
            output_dir,
            "test_entity",
            run_context
        )
