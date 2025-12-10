"""
Tests for the UnifiedLoaderImpl.
"""

# pylint: disable=redefined-outer-name, protected-access
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from bioetl.domain.clients.base.output.contracts import WriteResult
from bioetl.infrastructure.output.converters.factories import (
    default_output_frame_converter,
)
from bioetl.infrastructure.output.unified_loader_impl import (
    UnifiedLoaderImpl,
)


@pytest.fixture
def mock_writer_fixture():
    """Fixture for mock writer."""
    return MagicMock()


@pytest.fixture
def mock_metadata_writer_fixture():
    """Fixture for mock metadata writer."""
    return MagicMock()


@pytest.fixture
def mock_quality_reporter():
    """Fixture for mock quality reporter."""
    reporter = MagicMock()
    reporter.build_quality_report.return_value = pd.DataFrame(
        {"column": ["a"], "null_count": [0]}
    )
    reporter.build_correlation_report.return_value = pd.DataFrame(
        {"column": ["a"], "a": [1.0]}
    )
    return reporter


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
    mock_quality_reporter,
    mock_config_fixture,
    mock_atomic_op,
):
    """Fixture for unified writer."""
    return UnifiedLoaderImpl(
        mock_writer_fixture,
        mock_metadata_writer_fixture,
        mock_quality_reporter,
        mock_config_fixture,
        atomic_op=mock_atomic_op,
    )


def test_write_result_success(
    unified_writer,
    mock_writer_fixture,
    mock_metadata_writer_fixture,
    mock_quality_reporter,
    run_context_factory,
    tmp_path,
):
    """Test successful write result handling."""
    # Arrange
    run_context = run_context_factory()
    df = pd.DataFrame({"a": [1, 2]})
    output_dir = tmp_path / "out"

    # Mock writer side effect to create the file
    def create_file(df, path, **kwargs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return WriteResult(
            path=path, row_count=len(df), checksum="abc", duration_sec=0.1
        )

    mock_writer_fixture.write.side_effect = create_file

    # Patch checksum function
    with patch(
        "bioetl.infrastructure.output.unified_loader_impl.compute_file_sha256"
    ) as mock_checksum:
        mock_checksum.side_effect = [
            "real_checksum",
            "qc_quality",
            "qc_correlation",
        ]

        # Act
        result = unified_writer.load(df, output_dir, run_context)

        # Assert
        assert result.row_count == 2
        assert result.checksum == "real_checksum"

        # Verify calls
        mock_writer_fixture.write.assert_called_once()
        mock_metadata_writer_fixture.write_meta.assert_called_once()
        assert mock_checksum.call_count == 3
        mock_quality_reporter.build_quality_report.assert_called_once()
        mock_quality_reporter.build_correlation_report.assert_called_once()


def test_unified_writer_delegates_atomicity(
    unified_writer,
    mock_writer_fixture,
    mock_atomic_op,
    mock_quality_reporter,
    run_context_factory,
    tmp_path,
):
    """Test that UnifiedOutputWriterImpl delegates to AtomicFileOperation."""
    # Arrange
    run_context = run_context_factory()
    df = pd.DataFrame({"a": [1]})
    output_dir = tmp_path / "out"

    mock_writer_fixture.write.return_value = WriteResult(
        path=output_dir / "test.csv", row_count=1, checksum="abc", duration_sec=0.1
    )

    with patch(
        "bioetl.infrastructure.output.unified_loader_impl.compute_file_sha256"
    ) as mock_checksum:
        mock_checksum.side_effect = ["abc", "qc1", "qc2"]

        # Act
        unified_writer.load(df, output_dir, run_context)

        # Assert
        assert mock_atomic_op.write_atomic.call_count == 3
        args_list = mock_atomic_op.write_atomic.call_args_list
        assert args_list[0][0][0] == output_dir / "test_entity.csv"
        assert args_list[1][0][0].name == "quality_report_table.csv"
        assert args_list[2][0][0].name == "correlation_report_table.csv"


def test_unified_writer_column_order_and_fill(
    unified_writer,
    mock_writer_fixture,
    mock_quality_reporter,
    mock_metadata_writer_fixture,
    run_context_factory,
    tmp_path,
):
    """Unified writer should respect column order and fill missing columns."""

    run_context = run_context_factory()
    df = pd.DataFrame({"b": [1]})
    output_dir = tmp_path / "out"
    captured_df: pd.DataFrame | None = None

    def capture_df(df_to_write, path, **kwargs):
        nonlocal captured_df
        captured_df = df_to_write.copy()
        return WriteResult(
            path=path,
            row_count=len(df_to_write),
            checksum="",
            duration_sec=0.0,
        )

    mock_writer_fixture.write.side_effect = capture_df

    with patch(
        "bioetl.infrastructure.output.unified_loader_impl.compute_file_sha256",
        return_value="chk",
    ):
        result = unified_writer.load(
            df,
            output_dir,
            run_context,
            column_order=["a", "b", "c"],
        )

    assert result.row_count == 1
    assert captured_df is not None
    assert list(captured_df.columns) == ["a", "b", "c"]
    assert pd.isna(captured_df.loc[0, "a"])
    assert captured_df.loc[0, "b"] == 1
    assert pd.isna(captured_df.loc[0, "c"])
    mock_metadata_writer_fixture.write_meta.assert_called_once()


def test_stable_sort_false(unified_writer, mock_config_fixture, run_context_factory):
    """Test behavior when stable_sort is False."""
    mock_config_fixture.stable_sort = False
    run_context = run_context_factory()
    df = pd.DataFrame({"b": [2], "a": [1]})

    result_df = unified_writer._stable_sort(df, run_context)

    # Should preserve order
    assert list(result_df.columns) == ["b", "a"]
    assert result_df.iloc[0]["b"] == 2


def test_stable_sort_columns_and_rows(
    unified_writer, mock_config_fixture, run_context_factory
):
    """Test stable sort of columns and rows."""
    mock_config_fixture.stable_sort = True

    run_context = run_context_factory(
        config={"hashing": {"business_key_fields": ["id"]}},
    )

    df = pd.DataFrame({"id": [2, 1, 3], "b": [20, 10, 30], "a": [200, 100, 300]})

    result_df = unified_writer._stable_sort(df, run_context)

    # Columns sorted alphabetically
    assert list(result_df.columns) == ["a", "b", "id"]

    # Rows sorted by 'id'
    assert result_df["id"].tolist() == [1, 2, 3]
    assert result_df["a"].tolist() == [100, 200, 300]


def test_write_result_raises_on_no_inner_result(
    unified_writer, mock_writer_fixture, run_context_factory, tmp_path
):
    """Test error raised when inner writer returns nothing."""
    # Arrange
    run_context = run_context_factory()
    df = pd.DataFrame({"a": [1]})
    output_dir = tmp_path / "out"

    # inner writer returns None (mock default)
    mock_writer_fixture.write.return_value = None

    # Act & Assert
    with pytest.raises(RuntimeError, match="Inner writer did not return result"):
        unified_writer.load(df, output_dir, run_context)


def test_write_result_records_metric_on_failure(
    mock_metadata_writer_fixture,
    mock_quality_reporter,
    mock_config_fixture,
    mock_atomic_op,
    run_context_factory,
    tmp_path,
):
    """Failures should increment output write error metric."""

    metrics = MagicMock()
    writer = MagicMock()
    writer.write.side_effect = ValueError("boom")

    writer_impl = UnifiedLoaderImpl(
        writer,
        mock_metadata_writer_fixture,
        mock_quality_reporter,
        mock_config_fixture,
        atomic_op=mock_atomic_op,
        metrics=metrics,
    )

    with pytest.raises(ValueError):
        writer_impl.load(
            pd.DataFrame({"a": [1]}), tmp_path, run_context_factory()
        )

    metrics.inc_counter.assert_called_once_with(
        "output_write_errors_total", {"entity": "test_entity", "error_type": "ValueError"}
    )


def test_unified_writer_applies_converter_rename(
    mock_metadata_writer_fixture,
    mock_quality_reporter,
    mock_config_fixture,
    mock_atomic_op,
    run_context_factory,
    tmp_path,
):
    writer = MagicMock()
    captured_df: pd.DataFrame | None = None

    def capture_df(df_to_write, path, **kwargs):
        nonlocal captured_df
        captured_df = df_to_write.copy()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return WriteResult(
            path=path, row_count=len(df_to_write), checksum="", duration_sec=0.0
        )

    writer.write.side_effect = capture_df

    converter = default_output_frame_converter("rename_columns")
    writer_impl = UnifiedLoaderImpl(
        writer,
        mock_metadata_writer_fixture,
        mock_quality_reporter,
        mock_config_fixture,
        atomic_op=mock_atomic_op,
        converter=converter,
    )

    df = pd.DataFrame({"a_col": [1], "b_col": [2]})
    with patch(
        "bioetl.infrastructure.output.unified_loader_impl.compute_file_sha256",
        return_value="chk",
    ):
        writer_impl.load(
            df,
            tmp_path / "out",
            run_context_factory(),
            column_order=["a_col", "b_col"],
        )

    assert captured_df is not None
    assert list(captured_df.columns) == ["a-col", "b-col"]


def test_unified_writer_applies_converter_dropna(
    mock_metadata_writer_fixture,
    mock_quality_reporter,
    mock_config_fixture,
    mock_atomic_op,
    run_context_factory,
    tmp_path,
):
    writer = MagicMock()

    def create_file(df_to_write, path, **kwargs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return WriteResult(
            path=path, row_count=len(df_to_write), checksum="", duration_sec=0.0
        )

    writer.write.side_effect = create_file

    converter = default_output_frame_converter("dropna")
    writer_impl = UnifiedLoaderImpl(
        writer,
        mock_metadata_writer_fixture,
        mock_quality_reporter,
        mock_config_fixture,
        atomic_op=mock_atomic_op,
        converter=converter,
    )

    df = pd.DataFrame({"a": [None], "b": [None]})
    with patch(
        "bioetl.infrastructure.output.unified_loader_impl.compute_file_sha256",
        return_value="chk",
    ):
        result = writer_impl.load(
            df,
            tmp_path / "out",
            run_context_factory(),
            column_order=["a", "b"],
        )

    assert result.row_count == 0
