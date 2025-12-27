"""Tests for run_id propagation through the data pipeline.

Verifies that run_id is consistently propagated:
- Through BronzeWriter (metadata)
- Through DeltaWriter (Silver layer records)
- Through logs
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pyarrow as pa
import pytest

from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.domain.config import DQConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.types import BatchID, RunID, RunType, ValidationResult


@pytest.fixture
def run_id() -> RunID:
    """Generate a unique run ID for testing."""
    return uuid4()


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind.return_value = logger
    return logger


@pytest.fixture
def mock_storage():
    """Create mock storage with Bronze and Silver writers."""
    storage = MagicMock()
    storage.write_bronze = AsyncMock()
    storage.write_silver = AsyncMock()
    storage.write_gold = AsyncMock()
    return storage


@pytest.fixture
def mock_quarantine():
    """Create mock quarantine port."""
    quarantine = AsyncMock()
    quarantine.write = AsyncMock()
    return quarantine


@pytest.fixture
def pipeline_context(run_id: RunID, mock_logger) -> PipelineContext:
    """Create pipeline context with the run_id."""
    return PipelineContext(
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def mock_services(mock_storage, mock_quarantine):
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineServices)
    services.storage = mock_storage
    services.metrics = (
        MagicMock()
    )  # Per Unified Observability Contract, metrics is never None
    services.quarantine = mock_quarantine
    return services


@pytest.fixture
def mock_gold_validator():
    """Create mock gold validator."""
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(valid=True))
    return validator


@pytest.fixture
def silver_schema() -> pa.Schema:
    """Create a sample silver schema."""
    return pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("value", pa.string()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )


@pytest.mark.unit
class TestRunIdPropagation:
    """Tests for run_id propagation through the pipeline."""

    @pytest.mark.asyncio
    async def test_same_run_id_in_bronze_and_silver(
        self,
        run_id: RunID,
        pipeline_context: PipelineContext,
        mock_services: MagicMock,
        mock_storage: MagicMock,
        silver_schema: pa.Schema,
        mock_gold_validator: MagicMock,
    ) -> None:
        """Test that the same run_id is propagated to both Bronze and Silver."""

        # Create a transform that returns the record with lineage fields
        # (simulating what BaseTransformer.entity_to_silver_record does)
        async def transform(ctx, record):
            return {
                "id": str(record.get("id")),
                "value": record.get("value"),
                "_run_id": str(ctx.run_id),
                "_run_type": ctx.run_type.value,
                "_ingestion_ts": ctx.started_at.isoformat(),
            }

        def gold_filter(ctx, record):
            return False  # Don't write to gold for this test

        config = RecordProcessorConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            silver_schema=silver_schema,
            gold_schema=MagicMock(),
            dq_config=DQConfig(),
            table_config=TableConfig(primary_keys=["id"]),
        )

        processor = RecordProcessor(
            services=mock_services,
            error_classifier=ErrorClassifier(),
            context=pipeline_context,
            config=config,
            transform_callback=transform,
            gold_filter_callback=gold_filter,
            gold_transform_callback=lambda c, r: r,
            gold_validator=mock_gold_validator,
        )

        # Process a batch
        records = [{"id": 1, "value": "test"}]
        batch_id = BatchID(uuid4())

        await processor.process_batch(records, batch_id)

        # Verify Bronze was called with run_id
        mock_storage.write_bronze.assert_called_once()
        bronze_call_kwargs = mock_storage.write_bronze.call_args[1]
        assert bronze_call_kwargs["run_id"] == run_id
        assert bronze_call_kwargs["run_type"] == RunType.INCREMENTAL

        # Verify Silver was called with run_id in records
        mock_storage.write_silver.assert_called_once()
        silver_call_kwargs = mock_storage.write_silver.call_args[1]
        silver_records = silver_call_kwargs["records"]

        assert len(silver_records) == 1
        assert silver_records[0]["_run_id"] == str(run_id)
        assert silver_records[0]["_run_type"] == RunType.INCREMENTAL.value

    @pytest.mark.asyncio
    async def test_run_id_consistency_across_multiple_batches(
        self,
        run_id: RunID,
        pipeline_context: PipelineContext,
        mock_services: MagicMock,
        mock_storage: MagicMock,
        silver_schema: pa.Schema,
        mock_gold_validator: MagicMock,
    ) -> None:
        """Test that the same run_id is used across multiple batches."""

        async def transform(ctx, record):
            return {
                "id": str(record.get("id")),
                "value": record.get("value"),
                "_run_id": str(ctx.run_id),
                "_run_type": ctx.run_type.value,
                "_ingestion_ts": ctx.started_at.isoformat(),
            }

        def gold_filter(ctx, record):
            return False

        config = RecordProcessorConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            silver_schema=silver_schema,
            gold_schema=MagicMock(),
            dq_config=DQConfig(),
            table_config=TableConfig(primary_keys=["id"]),
        )

        processor = RecordProcessor(
            services=mock_services,
            error_classifier=ErrorClassifier(),
            context=pipeline_context,
            config=config,
            transform_callback=transform,
            gold_filter_callback=gold_filter,
            gold_transform_callback=lambda c, r: r,
            gold_validator=mock_gold_validator,
        )

        # Process multiple batches
        for i in range(3):
            records = [{"id": i, "value": f"test_{i}"}]
            batch_id = BatchID(uuid4())
            await processor.process_batch(records, batch_id)

        # Verify all Bronze calls have the same run_id
        assert mock_storage.write_bronze.call_count == 3
        for call in mock_storage.write_bronze.call_args_list:
            assert call[1]["run_id"] == run_id

        # Verify all Silver calls have the same run_id in records
        assert mock_storage.write_silver.call_count == 3
        for call in mock_storage.write_silver.call_args_list:
            silver_records = call[1]["records"]
            for record in silver_records:
                assert record["_run_id"] == str(run_id)

    @pytest.mark.asyncio
    async def test_different_run_types_propagated_correctly(
        self,
        mock_logger,
        mock_services: MagicMock,
        mock_storage: MagicMock,
        silver_schema: pa.Schema,
        mock_gold_validator: MagicMock,
    ) -> None:
        """Test that different run types are correctly propagated."""
        for run_type in [RunType.INCREMENTAL, RunType.BACKFILL, RunType.REBUILD]:
            # Reset mocks
            mock_storage.write_bronze.reset_mock()
            mock_storage.write_silver.reset_mock()

            run_id = uuid4()
            context = PipelineContext(
                run_id=run_id,
                run_type=run_type,
                logger=mock_logger,
            )

            async def transform(ctx, record):
                return {
                    "id": str(record.get("id")),
                    "value": record.get("value"),
                    "_run_id": str(ctx.run_id),
                    "_run_type": ctx.run_type.value,
                    "_ingestion_ts": ctx.started_at.isoformat(),
                }

            def gold_filter(ctx, record):
                return False

            config = RecordProcessorConfig(
                pipeline_name="test_pipeline",
                provider="test",
                entity_type="entity",
                silver_schema=silver_schema,
                gold_schema=MagicMock(),
                dq_config=DQConfig(),
                table_config=TableConfig(primary_keys=["id"]),
            )

            processor = RecordProcessor(
                services=mock_services,
                error_classifier=ErrorClassifier(),
                context=context,
                config=config,
                transform_callback=transform,
                gold_filter_callback=gold_filter,
                gold_transform_callback=lambda c, r: r,
                gold_validator=mock_gold_validator,
            )

            records = [{"id": 1, "value": "test"}]
            batch_id = BatchID(uuid4())

            await processor.process_batch(records, batch_id)

            # Verify Bronze
            bronze_kwargs = mock_storage.write_bronze.call_args[1]
            assert bronze_kwargs["run_type"] == run_type

            # Verify Silver
            silver_records = mock_storage.write_silver.call_args[1]["records"]
            assert silver_records[0]["_run_type"] == run_type.value
