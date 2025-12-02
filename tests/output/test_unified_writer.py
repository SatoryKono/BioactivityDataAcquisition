"""
Tests for the UnifiedOutputWriter.
"""
# pylint: disable=redefined-outer-name, protected-access
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from bioetl.core.models import RunContext
from bioetl.output.contracts import WriteResult
from bioetl.output.unified_writer import UnifiedOutputWriter


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
def unified_writer(
    mock_writer_fixture,
    mock_metadata_writer_fixture,
    mock_config_fixture
):
    """Fixture for unified writer."""
    return UnifiedOutputWriter(
        mock_writer_fixture,
        mock_metadata_writer_fixture,
        mock_config_fixture
    )


@pytest.fixture
def run_context():
    """Fixture for run context."""
    return RunContext(
        run_id="test-run",
        entity_name="test_entity",
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

    # Mock checksum computation to avoid reading non-existent file
    with patch.object(
        unified_writer,
        "_compute_checksum",
        return_value="real_checksum"
    ):
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


def test_atomic_write_retry(unified_writer, mock_writer_fixture, tmp_path):
    """Test atomic write retry logic."""
    # Arrange
    df = pd.DataFrame({"a": [1]})
    output_path = tmp_path / "target.csv"
    tmp_file = output_path.with_suffix(".tmp")

    # Create dummy tmp file so move works
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mock_writer_fixture.write.return_value = WriteResult(
        path=tmp_file,
        row_count=1,
        checksum="xyz",
        duration_sec=0.1
    )

    # Mock shutil.move to fail then succeed
    with patch("shutil.move") as mock_move, \
         patch("os.remove"), \
         patch.object(
             unified_writer,
             "_compute_checksum",
             return_value="hash"
         ):

        # Side effect: Raise OSError twice, then succeed
        mock_move.side_effect = [OSError("Locked"), OSError("Locked"), None]

        # Act
        unified_writer._atomic_write(df, output_path)

        # Assert
        assert mock_move.call_count == 3


def test_compute_checksum(unified_writer, tmp_path):
    """Test checksum computation."""
    # Arrange
    file_path = tmp_path / "test.txt"
    file_path.write_text("content", encoding="utf-8")

    # Act
    checksum = unified_writer._compute_checksum(file_path)

    # Assert
    assert isinstance(checksum, str)
    assert len(checksum) == 64  # SHA256 hex
