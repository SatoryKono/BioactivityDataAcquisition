"""Unit tests for RecordProcessor."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.application.core.transformers.gold import DefaultGoldTransformer
from bioetl.domain.config import PipelineConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import DataQualityError, DataQualityThresholdError
from bioetl.domain.ports.validation import ValidationResult
from bioetl.domain.types import BatchID, RunType
from bioetl.infrastructure.config import get_pipeline_config


# --- Fixtures ---
@pytest.fixture
def mock_storage():
    """Mock storage port."""
    storage = AsyncMock()
    storage.write_bronze = AsyncMock()
    storage.write_silver = AsyncMock()
    storage.write_gold = AsyncMock()
    return storage


@pytest.fixture
def mock_quarantine():
    """Mock quarantine port."""
    quarantine = AsyncMock()
    quarantine.write = AsyncMock()
    return quarantine


@pytest.fixture
def mock_metrics():
    """Mock metrics port."""
    metrics = MagicMock()
    metrics.increment = MagicMock()
    return metrics


@pytest.fixture
def mock_services(mock_storage, mock_quarantine, mock_metrics):
    """Mock PipelineServices."""
    services = MagicMock()
    services.storage = mock_storage
    services.quarantine = mock_quarantine
    services.metrics = mock_metrics
    return services


@pytest.fixture
def mock_error_classifier():
    """Mock ErrorClassifier."""
    classifier = ErrorClassifier()
    return classifier


@pytest.fixture
def mock_context():
    """Mock PipelineContext."""
    return PipelineContext.create(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=MagicMock(),
    )


@pytest.fixture
def mock_gold_transformer():
    """Mock GoldTransformer."""
    transformer = MagicMock()
    transformer.should_process.return_value = True
    transformer.transform.side_effect = lambda ctx, rec: rec  # Identity transform
    return transformer


@pytest.fixture
def record_processor(
    mock_services, mock_error_classifier, mock_context, mock_gold_transformer
):
    """Create a RecordProcessor instance."""
    table_config = TableConfig(
        primary_keys=["id"],
        silver_table="silver_test",
        gold_table="gold_test",
        silver_write_mode="append",
        gold_write_mode="append",
    )
    config = RecordProcessorConfig(
        pipeline_name="test",
        provider="test",
        entity_type="test",
        silver_schema=MagicMock(),
        gold_schema=MagicMock(),
        dq_config=None,
        table_config=table_config,
    )

    # Mock callbacks
    async def transform_callback(ctx, record):
        return record

    gold_validator = MagicMock()
    gold_validator.validate = MagicMock(return_value=ValidationResult(valid=True))

    return RecordProcessor(
        services=mock_services,
        error_classifier=mock_error_classifier,
        context=mock_context,
        config=config,
        transform_callback=transform_callback,
        gold_transformer=mock_gold_transformer,
        gold_validator=gold_validator,
    )


# --- Tests ---
@pytest.mark.unit
class TestRecordProcessorInit:
    """Tests for RecordProcessor initialization."""

    def test_init_stores_dependencies(self, record_processor, mock_storage):
        """Test that initialization stores all dependencies."""
        assert record_processor._bronze_handler._ctx.storage is mock_storage


@pytest.mark.unit
class TestRecordProcessorProcessBatch:
    """Tests for process_batch method."""

    async def test_process_batch_writes_to_all_layers(
        self, record_processor, mock_storage, mock_gold_transformer
    ):
        """Test that process_batch writes to Bronze, Silver, and Gold."""

        # Override mock_gold_transformer behavior for this test
        mock_gold_transformer.should_process.side_effect = lambda ctx, r: r["value"] > 5

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

    async def test_process_batch_propagates_run_id_to_all_layers(
        self, record_processor, mock_storage, mock_context
    ):
        """Test that the same run_id is passed to Bronze and Silver writes.

        This verifies the requirement: one run = one UUID everywhere.
        """
        records = [{"id": "1", "value": 10}]
        batch_id = BatchID(uuid4())

        await record_processor.process_batch(records, batch_id)

        # Verify Bronze write received run_id and run_type from context
        bronze_call_kwargs = mock_storage.write_bronze.call_args[1]
        assert bronze_call_kwargs["run_id"] == mock_context.run_id
        assert bronze_call_kwargs["run_type"] == mock_context.run_type

        # Verify Silver records contain the same run_id
        silver_call_kwargs = mock_storage.write_silver.call_args[1]
        silver_records = silver_call_kwargs["records"]
        for record in silver_records:
            assert record["_run_id"] == str(mock_context.run_id)
            assert record["_run_type"] == mock_context.run_type.value

    async def test_process_batch_no_gold_records(
        self, record_processor, mock_storage, mock_gold_transformer
    ):
        """Test process_batch when no records pass gold filter."""
        mock_gold_transformer.should_process.return_value = False

        records = [
            {"id": "1", "value": 1},
            {"id": "2", "value": 2},
        ]
        batch_id = BatchID(uuid4())

        result = await record_processor.process_batch(records, batch_id)

        assert result.gold_count == 0
        mock_storage.write_gold.assert_not_called()

    async def test_process_batch_handles_transform_error(
        self, mock_services, mock_error_classifier, mock_context, mock_gold_transformer
    ):
        """Test that transform errors result in quarantine."""

        async def failing_transform(ctx, record):
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        gold_validator = MagicMock()
        gold_validator.validate = MagicMock(return_value=ValidationResult(valid=True))

        processor = RecordProcessor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=config,
            transform_callback=failing_transform,
            gold_transformer=mock_gold_transformer,
            gold_validator=gold_validator,
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
        # Quarantine logic is now internal to Processor via QuarantineManager -> Port
        mock_services.quarantine.write.assert_called_once()

    async def test_process_batch_raises_non_data_quality_errors(
        self, mock_services, mock_error_classifier, mock_context, mock_gold_transformer
    ):
        """Test that non-data-quality errors are re-raised."""
        from bioetl.domain.exceptions import LockLostError

        async def failing_transform(ctx, record):
            raise LockLostError("resource_key", "test_run_id")

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        gold_validator = MagicMock()
        gold_validator.validate = MagicMock(return_value=ValidationResult(valid=True))

        processor = RecordProcessor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=config,
            transform_callback=failing_transform,
            gold_transformer=mock_gold_transformer,
            gold_validator=gold_validator,
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
        monkeypatch,
        mock_services,
        mock_error_classifier,
        mock_context,
        mock_gold_transformer
    ):
        """DQ hard threshold берётся из YAML и вызывает ошибку при превышении."""

        pipeline_name = "tmp_pipeline"
        _write_temp_pipeline_config(tmp_path, pipeline_name, 0.1, 0.4)
        monkeypatch.chdir(tmp_path)
        get_pipeline_config.cache_clear()

        config = get_pipeline_config(pipeline_name)

        async def transform(ctx, record):
            if record.get("id") == "bad":
                raise DataQualityError("invalid")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        processor_config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=config.dq,
        )

        gold_validator = MagicMock()
        gold_validator.validate = MagicMock(return_value=ValidationResult(valid=True))

        processor = RecordProcessor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=processor_config,
            transform_callback=transform,
            gold_transformer=mock_gold_transformer,
            gold_validator=gold_validator,
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
        monkeypatch,
        mock_services,
        mock_error_classifier,
        mock_context,
        mock_gold_transformer
    ):
        """Высокий soft-порог из YAML отключает предупреждения при низкой доле ошибок."""

        pipeline_name = "tmp_pipeline_alt"
        _write_temp_pipeline_config(tmp_path, pipeline_name, 0.8, 0.95)
        monkeypatch.chdir(tmp_path)
        get_pipeline_config.cache_clear()

        config = get_pipeline_config(pipeline_name)

        async def transform(ctx, record):
            if record.get("id") == "bad":
                raise DataQualityError("invalid")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        processor_config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=config.dq,
        )

        gold_validator = MagicMock()
        gold_validator.validate = MagicMock(return_value=ValidationResult(valid=True))

        processor = RecordProcessor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            config=processor_config,
            transform_callback=transform,
            gold_transformer=mock_gold_transformer,
            gold_validator=gold_validator,
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


def _write_temp_pipeline_config(tmp_path, name, soft, hard):
    """Helper to write temp config."""
    try:
        provider, entity = name.split("_", 1)
    except ValueError:
        provider, entity = "tmp", name

    config_dir = tmp_path / "configs" / "pipelines" / provider
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / f"{entity}.yaml"

    content = f"""
pipeline_name: {name}
provider: tmp
entity_type: {name}
source:
  type: api
  endpoint_url: http://test.local/
  rate_limit: 10
  format: json
primary_keys: ["entity_id"]
silver_table: silver_{name}
dq:
  soft_fail_threshold: {soft}
  hard_fail_threshold: {hard}
"""
    config_file.write_text(content)
