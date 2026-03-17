"""Unit tests for pipeline_builder module functions."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.services.pipeline_builder import (
    BatchProcessingComponents,
    create_batch_processing_components,
    create_checkpoint_manager,
    create_record_processor_from_pipeline,
)


@pytest.mark.unit
class TestBatchProcessingComponents:
    """Tests for BatchProcessingComponents dataclass."""

    def test_stores_three_components(self) -> None:
        """Dataclass holds batch_metrics, transformer, and writer."""
        bm = MagicMock()
        tf = MagicMock()
        wr = MagicMock()

        components = BatchProcessingComponents(
            batch_metrics=bm, transformer=tf, writer=wr
        )

        assert components.batch_metrics is bm
        assert components.transformer is tf
        assert components.writer is wr


@pytest.mark.unit
class TestCreateCheckpointManager:
    """Tests for create_checkpoint_manager."""

    @patch(
        "bioetl.composition.factories.services.pipeline_builder.CheckpointManagerService"
    )
    def test_creates_checkpoint_manager_service(self, mock_cls: MagicMock) -> None:
        """Creates CheckpointManagerService with all params."""
        expected = MagicMock()
        mock_cls.return_value = expected

        result = create_checkpoint_manager(
            checkpoint_port=MagicMock(),
            logger=MagicMock(),
            pipeline_name="test",
            run_id="r1",
            resume=True,
        )

        assert result is expected
        mock_cls.assert_called_once()

    @patch(
        "bioetl.composition.factories.services.pipeline_builder.CheckpointManagerService"
    )
    def test_passes_loading_strategy(self, mock_cls: MagicMock) -> None:
        """Loading strategy is forwarded to constructor."""
        mock_cls.return_value = MagicMock()
        strategy = MagicMock()

        create_checkpoint_manager(
            checkpoint_port=MagicMock(),
            logger=MagicMock(),
            pipeline_name="p",
            run_id="r",
            resume=False,
            loading_strategy=strategy,
        )

        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["loading_strategy"] is strategy


@pytest.mark.unit
class TestCreateBatchProcessingComponents:
    """Tests for create_batch_processing_components."""

    @patch("bioetl.composition.factories.services.pipeline_builder.BatchWriter")
    @patch("bioetl.composition.factories.services.pipeline_builder.BatchTransformer")
    @patch(
        "bioetl.composition.factories.services.pipeline_builder.BatchMetricsRecorderService"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_builder.QuarantineManagerService"
    )
    def test_returns_batch_processing_components(
        self,
        mock_quarantine: MagicMock,
        mock_batch_metrics: MagicMock,
        mock_batch_transformer: MagicMock,
        mock_batch_writer: MagicMock,
    ) -> None:
        """Returns BatchProcessingComponents with wired metrics, transformer, writer."""
        bm = MagicMock()
        mock_batch_metrics.return_value = bm
        tf = MagicMock()
        mock_batch_transformer.return_value = tf
        wr = MagicMock()
        mock_batch_writer.return_value = wr

        context = MagicMock()
        context.run_type.value = "incremental"
        context.logger = MagicMock()

        config = MagicMock()
        config.provider = "chembl"
        config.entity_type = "activity"
        config.pipeline_name = "chembl_activity"
        config.column_groups = ()

        services = MagicMock()

        result = create_batch_processing_components(
            services=services,
            context=context,
            config=config,
            error_classifier=MagicMock(),
            transform_callback=MagicMock(),
            gold_filter_callback=MagicMock(),
            gold_transform_callback=MagicMock(),
            gold_validator=MagicMock(),
        )

        assert isinstance(result, BatchProcessingComponents)
        assert result.batch_metrics is bm
        assert result.transformer is tf
        assert result.writer is wr


@pytest.mark.unit
class TestCreateRecordProcessorFromPipeline:
    """Tests for create_record_processor_from_pipeline."""

    def test_delegates_to_processor_fn(self) -> None:
        """Delegates to create_record_processor_fn with pipeline fields."""
        expected = MagicMock()
        create_fn = MagicMock(return_value=expected)

        pipeline = MagicMock()
        pipeline.config.pipeline_name = "test"
        pipeline.config.provider = "chembl"
        pipeline.config.entity_type = "activity"
        pipeline.config.dq = None
        pipeline.config.table.primary_keys = ["pk"]
        pipeline.config.effective_silver_table = "silver_table"
        pipeline.config.effective_gold_table = "gold_table"
        pipeline.config.table.silver_write_mode = "merge"
        pipeline.config.table.gold_write_mode = "overwrite"
        pipeline.config.table.on_schema_mismatch = "error"
        pipeline.config.column_groups = []
        pipeline.config.scd_config = None

        callbacks = SimpleNamespace(
            transform=MagicMock(),
            gold_filter=MagicMock(),
            gold_transform=MagicMock(),
        )

        result = create_record_processor_from_pipeline(
            pipeline=pipeline,
            silver_schema=None,
            gold_schema=MagicMock(),
            callbacks=callbacks,
            create_record_processor_fn=create_fn,
        )

        assert result is expected
        create_fn.assert_called_once()
