"""
Tests for the PipelineBase class.
"""
# pylint: disable=redefined-outer-name, protected-access
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.hooks import PipelineHookABC
from bioetl.application.pipelines.base import PipelineBase


class ConcretePipeline(PipelineBase):
    """A concrete implementation of PipelineBase for testing."""

    def extract(self, **_):
        """Mock extraction returning sample data."""
        return pd.DataFrame({"id": [1, 2], "val": ["x", "y"]})

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mock transformation adding a column."""
        df["transformed"] = True
        return df


@pytest.mark.unit
def test_pipeline_run_success(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_output_writer,
    tmp_path
):
    """Test a successful pipeline run."""
    # Arrange
    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        output_writer=mock_output_writer
    )

    output_path = tmp_path / "output.parquet"

    # Act
    result = pipeline.run(output_path=output_path)

    # Assert
    assert result.success
    assert result.row_count == 2
    assert len(result.stages) == 4  # extract, transform, validate, write

    # Verify logger calls
    mock_logger.info.assert_any_call(
        "Pipeline started",
        run_id=result.run_id
    )

    # Verify write called
    mock_output_writer.write_result.assert_called_once()


@pytest.mark.unit
def test_pipeline_dry_run(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_output_writer,
    tmp_path
):
    """Test a dry run of the pipeline."""
    # Arrange
    pipeline = ConcretePipeline(
        mock_config,
        mock_logger,
        mock_validation_service,
        mock_output_writer
    )

    # Act
    result = pipeline.run(output_path=tmp_path, dry_run=True)

    # Assert
    assert result.success

    stage_names = [s.stage_name for s in result.stages]
    assert "extract" in stage_names
    assert "transform" in stage_names
    assert "validate" in stage_names
    assert "write" not in stage_names

    mock_output_writer.write_result.assert_not_called()


@pytest.mark.unit
def test_pipeline_hooks(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_output_writer
):
    """Test that hooks are called correctly."""
    # Arrange
    pipeline = ConcretePipeline(
        mock_config,
        mock_logger,
        mock_validation_service,
        mock_output_writer
    )
    mock_hook = MagicMock(spec=PipelineHookABC)
    pipeline.add_hook(mock_hook)

    # Act
    pipeline.run(Path("dummy"), dry_run=True)

    # Assert lifecycle hooks (extract, transform, validate)
    assert mock_hook.on_stage_start.call_count >= 3
    assert mock_hook.on_stage_end.call_count >= 3

    # Check arguments for one call
    args, _ = mock_hook.on_stage_start.call_args_list[0]
    assert args[0] == "extract"


@pytest.mark.unit
def test_pipeline_error_hooks(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_output_writer
):
    """Test that error hooks are called on failure."""
    # Arrange
    pipeline = ConcretePipeline(
        mock_config,
        mock_logger,
        mock_validation_service,
        mock_output_writer
    )
    mock_hook = MagicMock(spec=PipelineHookABC)
    pipeline.add_hook(mock_hook)

    # Mock extract to fail
    pipeline.extract = MagicMock(side_effect=ValueError("Extraction failed"))

    # Act & Assert
    with pytest.raises(ValueError, match="Extraction failed"):
        pipeline.run(Path("dummy"))

    # Verify hook called
    mock_hook.on_error.assert_called_once()
    args, _ = mock_hook.on_error.call_args
    assert args[0] == "pipeline"
    assert isinstance(args[1], ValueError)


@pytest.mark.unit
def test_hashing_logic(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_output_writer
):
    """Test different scenarios for business key hashing."""
    # Scenario 1: Config with business_key_fields=["id"] and present column
    pipeline = ConcretePipeline(
        mock_config, mock_logger, mock_validation_service, mock_output_writer
    )
    df = pd.DataFrame({"id": [1], "val": ["x"]})
    res = pipeline._add_hash_columns(df)
    assert "hash_row" in res.columns
    assert "hash_business_key" in res.columns
    assert res["hash_business_key"].iloc[0] is not None

    # Scenario 2: Configured key missing in DF
    mock_config.hashing.business_key_fields = ["missing_col"]
    pipeline = ConcretePipeline(
        mock_config, mock_logger, mock_validation_service, mock_output_writer
    )
    res = pipeline._add_hash_columns(df)
    assert res["hash_business_key"].iloc[0] is None

    # Scenario 3: No keys configured
    mock_config.hashing.business_key_fields = []
    pipeline = ConcretePipeline(
        mock_config, mock_logger, mock_validation_service, mock_output_writer
    )
    res = pipeline._add_hash_columns(df)
    assert res["hash_business_key"].iloc[0] is None
