"""Unit tests for RecordProcessor."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.domain.config import TableConfig
from bioetl.domain.exceptions import DataQualityError, DataQualityThresholdError
from bioetl.domain.ports import MetricsPort
from bioetl.domain.types import BatchID, ValidationResult
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.config import get_pipeline_config
from tests.unit.application.core.record_processor_test_support import (
    _create_record_processor,
    _create_record_processor_config,
    _write_temp_pipeline_config,
)

pytest_plugins = ("tests.unit.application.core.transformer_test_support",)


@pytest.fixture
def mock_storage():
    """Create mock medallion storage for RecordProcessor tests."""
    storage = MagicMock()
    storage.write_bronze = AsyncMock()
    storage.write_silver = AsyncMock()
    storage.write_gold = AsyncMock()
    return storage


@pytest.fixture
def mock_services(mock_storage):
    """Create mock pipeline services used by the record processor."""
    services = MagicMock(spec=PipelineService)
    services.storage = mock_storage
    services.metrics = MagicMock(spec=MetricsPort)
    services.quarantine = MagicMock()
    services.quarantine.write = AsyncMock()
    services.quarantine.write_many = AsyncMock()
    return services


@pytest.fixture
def mock_gold_validator():
    """Create mock gold validator that accepts records by default."""
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(valid=True))
    return validator


@pytest.fixture
def record_processor(
    mock_services,
    mock_error_classifier,
    mock_context,
    transform_callback,
    gold_filter_callback,
    gold_transform_callback,
    mock_gold_validator,
):
    """Create RecordProcessor instance."""
    config = _create_record_processor_config(table_config=TableConfig())
    return _create_record_processor(
        services=mock_services,
        error_classifier=mock_error_classifier,
        context=mock_context,
        config=config,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        gold_validator=mock_gold_validator,
    )


@pytest.mark.unit
class TestRecordProcessorInit:
    """Tests for RecordProcessor initialization."""

    def test_init_stores_context(self, record_processor, mock_context):
        """Test that initialization stores context."""
        assert record_processor._context is mock_context

    def test_init_creates_internal_components(self, record_processor):
        """Test that initialization creates BatchTransformer and BatchWriter."""
        # RecordProcessor creates these internally (composition pattern)
        assert record_processor._transformer is not None
        assert record_processor._writer is not None
        assert record_processor._batch_metrics is not None


@pytest.mark.unit
class TestRecordProcessorProcessBatch:
    """Tests for process_batch method."""

    async def test_process_batch_writes_to_all_layers(
        self, record_processor, mock_storage
    ):
        """Test that process_batch writes to Bronze, Silver, and Gold."""
        records = [
            {"id": "1", "value": 10},  # Goes to gold (value > 5)
            {"id": "2", "value": 3},  # Not in gold
        ]
        batch_id = BatchID(uuid4())

        result = await record_processor.process_batch(records, batch_id)

        assert result.bronze_count == 2
        assert result.silver_count == 2
        assert result.gold_count == 1
        assert result.quarantined_count == 0
        mock_storage.write_bronze.assert_called_once()
        mock_storage.write_silver.assert_called_once()
        mock_storage.write_gold.assert_called_once()

    async def test_process_batch_propagates_run_identity_to_write_boundaries(
        self, record_processor, mock_storage, mock_context
    ):
        """Test that run identity is propagated via explicit storage kwargs.

        This verifies the requirement: one run = one UUID everywhere.
        """
        records = [{"id": "1", "value": 10}]
        batch_id = BatchID(uuid4())

        await record_processor.process_batch(records, batch_id)

        # Verify Bronze write received run_id and run_type from context
        bronze_call_kwargs = mock_storage.write_bronze.call_args[1]
        assert bronze_call_kwargs["run_id"] == mock_context.run_id
        assert bronze_call_kwargs["run_type"] == mock_context.run_type

        silver_call_kwargs = mock_storage.write_silver.call_args[1]
        assert silver_call_kwargs["run_id"] == mock_context.run_id
        assert silver_call_kwargs["run_type"] == mock_context.run_type
        silver_records = silver_call_kwargs["records"]
        for record in silver_records:
            assert "_run_id" not in record
            assert "_run_type" not in record

    async def test_process_batch_passes_silver_refs_to_gold_write(
        self, record_processor, mock_storage
    ):
        """Gold write receives lineage refs from the preceding Silver write."""
        silver_result = SilverWriteResult(
            table_name="test_provider.test_entity",
            table_path="/tmp/silver/test_provider/test_entity",
            delta_version=7,
            record_count=1,
        )
        mock_storage.write_silver.return_value = silver_result

        await record_processor.process_batch(
            [{"id": "1", "value": 10}],
            BatchID(uuid4()),
        )

        gold_call_kwargs = mock_storage.write_gold.call_args.kwargs
        assert gold_call_kwargs["silver_refs"] == [silver_result]

    async def test_process_batch_no_gold_records(self, record_processor, mock_storage):
        """Test process_batch when no records pass gold filter."""
        records = [
            {"id": "1", "value": 1},
            {"id": "2", "value": 2},
        ]
        batch_id = BatchID(uuid4())

        result = await record_processor.process_batch(records, batch_id)

        assert result.gold_count == 0

    async def test_process_batch_writes_normalized_silver_records(
        self,
        mock_services,
        mock_error_classifier,
        mock_context,
        gold_transform_callback,
        mock_gold_validator,
    ) -> None:
        """Silver writer should receive finalized staged records after normalization."""

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            return PreSilverRecord(
                entity_id="crossref:10.1000/abc",
                business_data={
                    "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
                    "publication_date": "2024-02",
                    "title": "  Example Title  ",
                },
                build_silver_record=build_silver_record,
            )

        def build_silver_record(ctx, entity_id, content_hash, index, business_data):
            return {
                "entity_id": entity_id,
                "content_hash": content_hash,
                **business_data,
            }

        def filter_gold(ctx, record):
            return True

        config = _create_record_processor_config(
            pipeline_name="crossref_publication",
            provider="crossref",
            entity_type="publication",
            table_config=TableConfig(primary_keys=("publication_doi",)),
        )
        processor = _create_record_processor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=config,
            transform_callback=transform,
            gold_filter_callback=filter_gold,
            gold_transform_callback=gold_transform_callback,
            gold_validator=mock_gold_validator,
        )

        await processor.process_batch([{"id": "1"}], BatchID(uuid4()))

        silver_records = mock_services.storage.write_silver.call_args.kwargs["records"]
        normalized = silver_records[0]
        assert normalized["entity_id"] == "crossref:10.1000/abc"
        assert normalized["publication_doi"] == "10.1000/abc"
        assert normalized["publication_date"] == "2024-02-29"
        assert normalized["title"] == "Example Title"
        assert isinstance(normalized["content_hash"], str)
        assert normalized["content_hash"]
        assert "_run_id" not in normalized
        assert "_run_type" not in normalized
        assert "_ingestion_ts" not in normalized
        mock_services.storage.write_gold.assert_called_once()

    async def test_process_batch_same_normalized_doi_produces_same_final_hash(
        self,
        mock_services,
        mock_error_classifier,
        mock_context,
        gold_transform_callback,
        mock_gold_validator,
    ) -> None:
        """Equivalent DOI inputs should converge to the same final content hash."""

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            return PreSilverRecord(
                entity_id=f"crossref:{record['id']}",
                business_data={
                    "publication_doi": record["doi"],
                    "title": "Same Title",
                },
                build_silver_record=build_silver_record,
            )

        def build_silver_record(ctx, entity_id, content_hash, index, business_data):
            return {
                "entity_id": entity_id,
                "content_hash": content_hash,
                **business_data,
            }

        config = _create_record_processor_config(
            pipeline_name="crossref_publication",
            provider="crossref",
            entity_type="publication",
            table_config=TableConfig(primary_keys=("publication_doi",)),
        )
        processor = _create_record_processor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=config,
            transform_callback=transform,
            gold_filter_callback=lambda c, r: True,
            gold_transform_callback=gold_transform_callback,
            gold_validator=mock_gold_validator,
        )

        await processor.process_batch(
            [
                {"id": "1", "doi": " HTTPS://doi.org/10.1000/ABC "},
                {"id": "2", "doi": "10.1000/abc"},
            ],
            BatchID(uuid4()),
        )

        silver_records = mock_services.storage.write_silver.call_args.kwargs["records"]
        assert silver_records[0]["publication_doi"] == "10.1000/abc"
        assert silver_records[1]["publication_doi"] == "10.1000/abc"
        assert silver_records[0]["content_hash"] == silver_records[1]["content_hash"]

    async def test_process_batch_handles_transform_error(
        self,
        mock_services,
        mock_error_classifier,
        mock_context,
        mock_gold_validator,
    ):
        """Test that transform errors result in quarantine."""

        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = _create_record_processor_config(
            pipeline_name="test",
            provider="test",
            entity_type="test",
        )

        processor = _create_record_processor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=config,
            transform_callback=failing_transform,
            gold_filter_callback=lambda c, r: True,
            gold_transform_callback=lambda c, r: r,
            gold_validator=mock_gold_validator,
        )

        records = [
            {"id": "good", "value": 10},
            {"id": "bad", "value": 5},  # Will fail transform
        ]
        batch_id = BatchID(uuid4())

        result = await processor.process_batch(records, batch_id)

        assert result.bronze_count == 2
        assert result.silver_count == 1
        assert result.quarantined_count == 1
        mock_services.quarantine.write_many.assert_called_once()

    async def test_process_batch_raises_non_data_quality_errors(
        self,
        mock_services,
        mock_error_classifier,
        mock_context,
        mock_gold_validator,
    ):
        """Test that non-data-quality errors are re-raised."""
        from bioetl.domain.exceptions import LockLostError

        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            raise LockLostError("resource_key", "test_run_id")

        config = _create_record_processor_config(
            pipeline_name="test",
            provider="test",
            entity_type="test",
        )

        processor = _create_record_processor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=config,
            transform_callback=failing_transform,
            gold_filter_callback=lambda c, r: True,
            gold_transform_callback=lambda c, r: r,
            gold_validator=mock_gold_validator,
        )

        records = [{"id": "test", "value": 5}]
        batch_id = BatchID(uuid4())

        with pytest.raises(LockLostError):
            await processor.process_batch(records, batch_id)

    async def test_process_batch_empty_records(self, record_processor, mock_storage):
        """Test process_batch with empty records list."""
        records = []
        batch_id = BatchID(uuid4())

        result = await record_processor.process_batch(records, batch_id)

        assert result.bronze_count == 0
        assert result.silver_count == 0
        assert result.gold_count == 0
        mock_storage.write_silver.assert_not_called()
        mock_storage.write_gold.assert_not_called()

    async def test_dq_thresholds_follow_yaml_hard_fail(
        self,
        tmp_path,
        mock_services,
        mock_error_classifier,
        mock_context,
        mock_gold_validator,
    ):
        """DQ hard threshold берётся из YAML и вызывает ошибку при превышении."""

        pipeline_name = "tmp_pipeline"
        _write_temp_pipeline_config(tmp_path, pipeline_name, 0.1, 0.4)
        get_pipeline_config.cache_clear()

        config = get_pipeline_config(
            pipeline_name,
            config_root=str(tmp_path / "configs"),
        )

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "bad":
                raise DataQualityError("invalid")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        processor_config = _create_record_processor_config(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            dq_config=config.dq,
        )

        processor = _create_record_processor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=processor_config,
            transform_callback=transform,
            gold_filter_callback=lambda c, r: True,
            gold_transform_callback=lambda c, r: r,
            gold_validator=mock_gold_validator,
        )

        records = [
            {"id": "good", "value": 1},
            {"id": "bad", "value": 2},
        ]

        with pytest.raises(DataQualityThresholdError):
            await processor.process_batch(records, BatchID(uuid4()))

        get_pipeline_config.cache_clear()

    async def test_dq_thresholds_follow_yaml_soft_threshold_prevents_warning(
        self,
        tmp_path,
        mock_services,
        mock_error_classifier,
        mock_context,
        mock_gold_validator,
    ):
        """Высокий soft-порог из YAML отключает предупреждения при низкой доле ошибок."""

        pipeline_name = "tmp_pipeline_alt"
        _write_temp_pipeline_config(tmp_path, pipeline_name, 0.8, 0.95)
        get_pipeline_config.cache_clear()

        config = get_pipeline_config(
            pipeline_name,
            config_root=str(tmp_path / "configs"),
        )

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "bad":
                raise DataQualityError("invalid")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        processor_config = _create_record_processor_config(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            dq_config=config.dq,
        )

        processor = _create_record_processor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=processor_config,
            transform_callback=transform,
            gold_filter_callback=lambda c, r: True,
            gold_transform_callback=lambda c, r: r,
            gold_validator=mock_gold_validator,
        )

        records = [
            {"id": "good", "value": 1},
            {"id": "bad", "value": 2},
        ]

        result = await processor.process_batch(records, BatchID(uuid4()))

        assert result.bronze_count == 2
        assert result.silver_count == 1
        assert result.gold_count == 1
        assert result.quarantined_count == 1
        mock_context.logger.warning.assert_not_called()

        get_pipeline_config.cache_clear()


@pytest.mark.unit
class TestRecordProcessorTracing:
    """Tests for tracing/span integration in RecordProcessor."""

    @pytest.fixture
    def mock_tracer(self):
        """Create a mock TracingPort with span support."""
        span = MagicMock()
        span.__enter__ = MagicMock(return_value=span)
        span.__exit__ = MagicMock(return_value=False)
        span.set_attribute = MagicMock()
        span.record_exception = MagicMock()

        tracer_impl = MagicMock()
        tracer_impl.start_as_current_span = MagicMock(return_value=span)

        tracer = MagicMock()
        tracer.get_tracer = MagicMock(return_value=tracer_impl)
        return tracer

    @pytest.fixture
    def traced_processor(
        self,
        mock_services,
        mock_error_classifier,
        mock_context,
        transform_callback,
        gold_filter_callback,
        gold_transform_callback,
        mock_gold_validator,
        mock_tracer,
    ):
        """Create RecordProcessor with tracing enabled."""
        config = _create_record_processor_config(table_config=TableConfig())
        return _create_record_processor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=config,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=mock_gold_validator,
            tracer=mock_tracer,
        )

    async def test_start_span_creates_span_with_attributes(
        self, traced_processor, mock_tracer
    ):
        """_start_span creates a tracing span with batch_id and record_count."""
        batch_id = BatchID(uuid4())
        records = [{"id": "1", "value": 10}]

        await traced_processor.process_batch(records, batch_id)

        tracer_impl = mock_tracer.get_tracer.return_value
        # At least write_bronze, transform, write_silver, write_gold spans
        assert tracer_impl.start_as_current_span.call_count >= 3

    async def test_span_records_transform_result_attributes(
        self, traced_processor, mock_tracer
    ):
        """_execute_transform_with_span sets silver/gold/quarantine counts on span."""
        batch_id = BatchID(uuid4())
        records = [{"id": "1", "value": 10}]

        await traced_processor.process_batch(records, batch_id)

        span = mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        # Transform span should set silver_count, gold_count, quarantined_count
        span.set_attribute.assert_any_call("bioetl.silver_count", 1)
        span.set_attribute.assert_any_call("bioetl.gold_count", 1)
        span.set_attribute.assert_any_call("bioetl.quarantined_count", 0)

    async def test_span_end_called_on_success(self, traced_processor, mock_tracer):
        """Spans are properly closed (__exit__) on success."""
        batch_id = BatchID(uuid4())
        records = [{"id": "1", "value": 10}]

        await traced_processor.process_batch(records, batch_id)

        span = mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        assert span.__exit__.call_count >= 3

    async def test_span_records_error_on_write_failure(
        self,
        mock_services,
        mock_error_classifier,
        mock_context,
        transform_callback,
        gold_filter_callback,
        gold_transform_callback,
        mock_gold_validator,
        mock_tracer,
    ):
        """_end_span records exception and sets error=True on failure."""
        mock_services.storage.write_bronze = AsyncMock(
            side_effect=RuntimeError("write failed")
        )
        config = _create_record_processor_config(table_config=TableConfig())
        processor = _create_record_processor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=config,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=mock_gold_validator,
            tracer=mock_tracer,
        )

        batch_id = BatchID(uuid4())
        records = [{"id": "1", "value": 10}]

        with pytest.raises(RuntimeError, match="write failed"):
            await processor.process_batch(records, batch_id)

        span = mock_tracer.get_tracer.return_value.start_as_current_span.return_value
        span.set_attribute.assert_any_call("error", True)
        span.record_exception.assert_called()

    async def test_on_error_callback_invoked_on_write_failure(
        self,
        mock_services,
        mock_error_classifier,
        mock_context,
        transform_callback,
        gold_filter_callback,
        gold_transform_callback,
        mock_gold_validator,
    ):
        """on_error callback in _execute_with_span is called when write raises."""
        write_error = RuntimeError("silver write failed")
        mock_services.storage.write_silver = AsyncMock(side_effect=write_error)

        config = _create_record_processor_config(table_config=TableConfig())
        processor = _create_record_processor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=config,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=mock_gold_validator,
        )

        batch_id = BatchID(uuid4())
        records = [{"id": "1", "value": 10}]

        with pytest.raises(RuntimeError, match="silver write failed"):
            await processor.process_batch(records, batch_id)

        # The on_error callback calls log_and_track_write_error on the writer
        # Verify the error was logged via context logger
        mock_context.logger.error.assert_called()
