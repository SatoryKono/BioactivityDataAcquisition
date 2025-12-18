"""Unit tests for RecordProcessor."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import DataQualityError, DataQualityThresholdError
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.config import get_pipeline_config


def _write_temp_pipeline_config(
    base_path: Path, pipeline_name: str, soft_threshold: float, hard_threshold: float
) -> Path:
    """Создаёт временную YAML-конфигурацию пайплайна с кастомными DQ-порогами."""

    provider, entity = pipeline_name.split("_", 1)
    config_dir = base_path / "configs" / "pipelines" / provider
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / f"{entity}.yaml"

    config_path.write_text(
        "\n".join(
            [
                f"pipeline_name: {pipeline_name}",
                f"provider: {provider}",
                f"entity_type: {entity}",
                "primary_keys: ['id']",
                "silver_table: 'tmp_silver'",
                "batch_size: 10",
                "checkpoint_interval: 100",
                "sink: {}",
                "dq_rules:",
                f"  soft_fail_threshold: {soft_threshold}",
                f"  hard_fail_threshold: {hard_threshold}",
            ]
        ),
        encoding="utf-8",
    )

    return config_path


@pytest.fixture
def mock_storage():
    """Create mock storage."""
    storage = AsyncMock()
    storage.write_bronze = AsyncMock()
    storage.write_silver = AsyncMock()
    storage.write_gold = AsyncMock()
    return storage

@pytest.fixture
def mock_metrics():
    """Create mock metrics."""
    metrics = AsyncMock()
    return metrics

@pytest.fixture
def mock_quarantine_port():
    """Create mock quarantine port."""
    port = AsyncMock()
    port.write = AsyncMock()
    return port

@pytest.fixture
def mock_services(mock_storage, mock_metrics, mock_quarantine_port):
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineServices)
    services.storage = mock_storage
    services.metrics = mock_metrics
    services.quarantine = mock_quarantine_port
    return services


@pytest.fixture
def mock_error_classifier():
    """Create mock error classifier."""
    return ErrorClassifier()


@pytest.fixture
def mock_context():
    """Create mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    return PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def transform_callback():
    """Create mock transform callback."""

    async def transform(ctx, record):
        return {"entity_id": record.get("id", "unknown"), "value": record.get("value")}

    return transform


@pytest.fixture
def gold_filter_callback():
    """Create mock gold filter callback."""

    def filter_gold(ctx, record):
        return record.get("value", 0) > 5

    return filter_gold


@pytest.fixture
def record_processor(
    mock_services,
    mock_error_classifier,
    mock_context,
    transform_callback,
    gold_filter_callback,
):
    """Create RecordProcessor instance."""
    return RecordProcessor(
        services=mock_services,
        error_classifier=mock_error_classifier,
        context=mock_context,
        pipeline_name="test_provider_test_entity",
        provider="test_provider",
        entity_type="test_entity",
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        silver_schema=MagicMock(),
    )


@pytest.mark.unit
class TestRecordProcessorInit:
    """Tests for RecordProcessor initialization."""

    def test_init_stores_dependencies(self, record_processor, mock_storage):
        """Test that initialization stores all dependencies."""
        assert record_processor._storage is mock_storage


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

        bronze, silver, gold, quarantined = await record_processor.process_batch(
            records, batch_id
        )

        assert bronze == 2
        assert silver == 2
        assert gold == 1
        assert quarantined == 0
        mock_storage.write_bronze.assert_called_once()
        mock_storage.write_silver.assert_called_once()
        mock_storage.write_gold.assert_called_once()

    async def test_process_batch_no_gold_records(self, record_processor, mock_storage):
        """Test process_batch when no records pass gold filter."""
        records = [
            {"id": "1", "value": 1},
            {"id": "2", "value": 2},
        ]
        batch_id = BatchID(uuid4())

        bronze, silver, gold, quarantined = await record_processor.process_batch(
            records, batch_id
        )

        assert gold == 0
        mock_storage.write_gold.assert_not_called()

    async def test_process_batch_handles_transform_error(
        self, mock_services, mock_error_classifier, mock_context
    ):
        """Test that transform errors result in quarantine."""

        async def failing_transform(ctx, record):
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        processor = RecordProcessor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            pipeline_name="test",
            provider="test",
            entity_type="test",
            transform_callback=failing_transform,
            gold_filter_callback=lambda c, r: True,
            silver_schema=MagicMock(),
        )

        records = [
            {"id": "good", "value": 10},
            {"id": "bad", "value": 5},  # Will fail transform
        ]
        batch_id = BatchID(uuid4())

        bronze, silver, gold, quarantined = await processor.process_batch(
            records, batch_id
        )

        assert bronze == 2
        assert silver == 1
        assert quarantined == 1
        # Quarantine logic is now internal to Processor via QuarantineManager -> Port
        mock_services.quarantine.write.assert_called_once()

    async def test_process_batch_raises_non_data_quality_errors(
        self, mock_services, mock_error_classifier, mock_context
    ):
        """Test that non-data-quality errors are re-raised."""
        from bioetl.domain.exceptions import LockLostError

        async def failing_transform(ctx, record):
            raise LockLostError("resource_key", "test_run_id")

        processor = RecordProcessor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            pipeline_name="test",
            provider="test",
            entity_type="test",
            transform_callback=failing_transform,
            gold_filter_callback=lambda c, r: True,
            silver_schema=MagicMock(),
        )

        records = [{"id": "test", "value": 5}]
        batch_id = BatchID(uuid4())

        with pytest.raises(LockLostError):
            await processor.process_batch(records, batch_id)

    async def test_process_batch_empty_records(self, record_processor, mock_storage):
        """Test process_batch with empty records list."""
        records = []
        batch_id = BatchID(uuid4())

        bronze, silver, gold, quarantined = await record_processor.process_batch(
            records, batch_id
        )

        assert bronze == 0
        assert silver == 0
        assert gold == 0
        mock_storage.write_silver.assert_not_called()
        mock_storage.write_gold.assert_not_called()

    async def test_dq_thresholds_follow_yaml_hard_fail(
        self,
        tmp_path,
        monkeypatch,
        mock_services,
        mock_error_classifier,
        mock_context,
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

        processor = RecordProcessor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            pipeline_name="test",
            provider="test",
            entity_type="test",
            transform_callback=transform,
            gold_filter_callback=lambda c, r: True,
            silver_schema=MagicMock(),
            dq_config=config.dq,
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

        processor = RecordProcessor(
            services=mock_services,
            error_classifier=mock_error_classifier,
            context=mock_context,
            pipeline_name="test",
            provider="test",
            entity_type="test",
            transform_callback=transform,
            gold_filter_callback=lambda c, r: True,
            silver_schema=MagicMock(),
            dq_config=config.dq,
        )

        records = [
            {"id": "good", "value": 1},
            {"id": "bad", "value": 2},
        ]

        bronze, silver, gold, quarantined = await processor.process_batch(
            records, BatchID(uuid4())
        )

        assert bronze == 2
        assert silver == 1
        assert gold == 1
        assert quarantined == 1
        mock_context.logger.warning.assert_not_called()

        get_pipeline_config.cache_clear()
