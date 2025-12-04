"""
Tests for the PipelineBase class.
"""
# pylint: disable=redefined-outer-name, protected-access
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.hooks import PipelineHookABC
from bioetl.application.pipelines.hooks_impl import ContinueOnErrorPolicyImpl
from bioetl.application.pipelines.base import PipelineBase
from bioetl.domain.errors import PipelineStageError


class ConcretePipeline(PipelineBase):
    """A concrete implementation of PipelineBase for testing."""

    def extract(self, **_):
        """Mock extraction returning sample data."""
        return pd.DataFrame({"id": [1, 2], "val": ["x", "y"]})

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mock transformation adding a column."""
        df["transformed"] = True
        return df


class DatasetPipeline(PipelineBase):
    """Pipeline that operates on a provided in-memory dataset."""

    def __init__(self, *args, dataset: pd.DataFrame, **kwargs):
        super().__init__(*args, **kwargs)
        self._dataset = dataset

    def extract(self, **_):
        return self._dataset.copy()

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.assign(processed=True)


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
    with pytest.raises(PipelineStageError) as exc_info:
        pipeline.run(Path("dummy"))

    assert isinstance(exc_info.value.cause, ValueError)
    assert str(exc_info.value.cause) == "Extraction failed"
    assert exc_info.value.stage == "extract"

    # Verify hook called
    assert mock_hook.on_error.call_count >= 1
    args, _ = mock_hook.on_error.call_args
    assert args[0] == "extract"  # stage name
    assert isinstance(args[1], PipelineStageError)
    assert args[1].stage == "extract"


@pytest.mark.unit
def test_error_policy_skip_stage(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_output_writer,
    tmp_path,
):
    """Пайплайн продолжает работу при политике SKIP."""

    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        output_writer=mock_output_writer,
        error_policy=ContinueOnErrorPolicyImpl(),
    )
    pipeline.extract = MagicMock(side_effect=ValueError("boom"))

    result = pipeline.run(output_path=tmp_path, dry_run=True)

    assert result.success
    assert result.row_count == 0


@pytest.mark.unit
def test_error_policy_retry(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_output_writer,
    tmp_path,
):
    """Пайплайн повторяет стадию при политике RETRY."""

    pipeline = ConcretePipeline(
        config=mock_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        output_writer=mock_output_writer,
        error_policy=ContinueOnErrorPolicyImpl(max_retries=1),
    )

    pipeline.extract = MagicMock(
        side_effect=[ValueError("temporary"), pd.DataFrame({"id": [1]})]
    )

    result = pipeline.run(output_path=tmp_path, dry_run=True)

    assert result.success
    assert result.row_count == 1
    assert pipeline.extract.call_count == 2


@pytest.mark.unit
def test_hashing_logic(
    mock_config,
    mock_logger,
    mock_validation_service,
    mock_output_writer
):
    """Test different scenarios for business key hashing."""
    # Scenario 1: Config with business_key_fields=["id"] and present column
    mock_config.hashing.business_key_fields = ["id"]
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


@pytest.mark.unit
def test_pipeline_dry_run_metadata_and_stages(
    pipeline_test_config,
    mock_logger,
    mock_validation_service,
    mock_output_writer,
    small_pipeline_df,
    tmp_path,
):
    """Dry-run returns accurate stage info and metadata."""
    pipeline = DatasetPipeline(
        config=pipeline_test_config,
        logger=mock_logger,
        validation_service=mock_validation_service,
        output_writer=mock_output_writer,
        dataset=small_pipeline_df,
    )

    result = pipeline.run(output_path=tmp_path, dry_run=True)

    assert result.success
    assert result.output_path is None
    assert result.errors == []
    assert [stage.stage_name for stage in result.stages] == [
        "extract",
        "transform",
        "validate",
    ]
    assert [stage.records_processed for stage in result.stages] == [
        len(small_pipeline_df),
        len(small_pipeline_df),
        len(small_pipeline_df),
    ]
    assert all(stage.errors == [] for stage in result.stages)
    assert result.meta["dry_run"] is True
    assert result.meta["row_count"] == len(small_pipeline_df)
    assert result.meta["provider"] == pipeline_test_config.provider
    assert result.meta["entity"] == pipeline_test_config.entity_name
    assert all(stage.duration_sec >= 0 for stage in result.stages)
