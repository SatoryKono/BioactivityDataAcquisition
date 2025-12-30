"""Unit tests for StorageFactory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.storage import (
    StorageAdapter,
    StorageContext,
    StorageFactory,
)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    """Create a mock metrics port."""
    return MagicMock()


@pytest.fixture
def mock_settings(tmp_path):
    """Settings for local run."""
    settings = MagicMock()
    settings.env = "dev"
    settings.bronze_path = tmp_path / "bronze"
    settings.silver_path = tmp_path / "silver"
    settings.gold_path = tmp_path / "gold"
    settings.checkpoint_path = tmp_path / "checkpoints"
    settings.data_dir = tmp_path
    settings.test_mode = True  # Default to test mode
    return settings


@pytest.fixture
def mock_config_minimal():
    """Minimal pipeline config without export options."""
    config = MagicMock()
    config.sink = {
        "bronze": MagicMock(save_json=False, path=None),
        "silver": MagicMock(csv_export=MagicMock(enabled=False), path=None),
        "gold": MagicMock(csv_export=MagicMock(enabled=False), path=None),
    }
    return config


@pytest.fixture
def mock_config_with_exports():
    """Pipeline config with CSV and JSON exports enabled."""
    config = MagicMock()

    bronze_config = MagicMock()
    bronze_config.save_json = True
    bronze_config.path = None  # Use settings fallback

    silver_csv = MagicMock()
    silver_csv.enabled = True
    silver_csv.path = "data/export/silver.csv"
    silver_csv.delimiter = ","
    silver_csv.header = True
    silver_csv.encoding = "utf-8"

    silver_config = MagicMock()
    silver_config.csv_export = silver_csv
    silver_config.path = None  # Use settings fallback

    gold_csv = MagicMock()
    gold_csv.enabled = True
    gold_csv.path = "data/export/gold.csv"
    gold_csv.delimiter = ";"
    gold_csv.header = True
    gold_csv.encoding = "utf-8"

    gold_config = MagicMock()
    gold_config.csv_export = gold_csv
    gold_config.path = None  # Use settings fallback

    config.sink = {
        "bronze": bronze_config,
        "silver": silver_config,
        "gold": gold_config,
    }
    return config


@pytest.fixture
def mock_config_empty_sink():
    """Pipeline config with empty sink."""
    config = MagicMock()
    config.sink = {}
    return config


@pytest.mark.unit
class TestStorageContext:
    """Tests for StorageContext dataclass."""

    def test_storage_context_creation(self, mock_logger):
        """Test StorageContext can be created with required fields."""
        adapter = MagicMock(spec=StorageAdapter)
        context = StorageContext(
            adapter=adapter,
            bronze_path=Path("/path/to/bronze"),
            silver_path=Path("/path/to/silver"),
            gold_path=Path("/path/to/gold"),
            checkpoints_path=Path("/path/to/checkpoints"),
        )

        assert context.adapter is adapter
        assert context.bronze_path == Path("/path/to/bronze")
        assert context.silver_path == Path("/path/to/silver")
        assert context.gold_path == Path("/path/to/gold")
        assert context.checkpoints_path == Path("/path/to/checkpoints")

    def test_storage_context_is_frozen(self, mock_logger):
        """Test StorageContext is immutable."""
        adapter = MagicMock(spec=StorageAdapter)
        context = StorageContext(
            adapter=adapter,
            bronze_path=Path("/path/to/bronze"),
            silver_path=Path("/path/to/silver"),
            gold_path=Path("/path/to/gold"),
            checkpoints_path=Path("/path/to/checkpoints"),
        )

        with pytest.raises(AttributeError):
            context.bronze_path = Path("/new/path")


@pytest.mark.unit
class TestStorageFactoryLocal:
    """Tests for StorageFactory.create() in local mode."""

    def test_local_run_uses_settings_paths(
        self,
        mock_settings,
        mock_config_minimal,
        mock_logger,
        mock_metrics,
    ):
        """Test that local runs use paths from settings."""
        with (
            patch("bioetl.composition.factories.storage_factory.BronzeWriter"),
            patch("bioetl.composition.factories.storage_factory.SilverWriter"),
            patch("bioetl.composition.factories.storage_factory.GoldWriter"),
        ):
            result = StorageFactory.create(
                settings=mock_settings,
                config=mock_config_minimal,
                logger=mock_logger,
                metrics=mock_metrics,
            )

            assert isinstance(result, StorageContext)
            assert result.bronze_path == mock_settings.bronze_path
            assert result.silver_path == mock_settings.silver_path
            assert result.gold_path == mock_settings.gold_path
            assert result.checkpoints_path == mock_settings.checkpoint_path

    def test_local_run_uses_yaml_paths_when_specified(
        self,
        mock_settings,
        mock_logger,
        mock_metrics,
    ):
        """Test that YAML paths override settings paths when specified."""
        config = MagicMock()
        config.sink = {
            "bronze": MagicMock(save_json=False, path="custom/bronze"),
            "silver": MagicMock(
                csv_export=MagicMock(enabled=False), path="custom/silver"
            ),
            "gold": MagicMock(csv_export=MagicMock(enabled=False), path="custom/gold"),
        }
        mock_settings.test_mode = False

        with (
            patch(
                "bioetl.composition.factories.storage_factory.BronzeWriter"
            ) as mock_bronze,
            patch(
                "bioetl.composition.factories.storage_factory.SilverWriter"
            ) as mock_delta,
            patch(
                "bioetl.composition.factories.storage_factory.GoldWriter"
            ) as mock_gold,
        ):
            result = StorageFactory.create(
                settings=mock_settings,
                config=config,
                logger=mock_logger,
                metrics=mock_metrics,
            )

            # Verify YAML paths are used
            assert result.bronze_path == Path("custom/bronze")
            assert result.silver_path == Path("custom/silver")
            assert result.gold_path == Path("custom/gold")

            # Verify writers received YAML paths
            bronze_call = mock_bronze.call_args[1]
            assert bronze_call["base_path"] == Path("custom/bronze")

            delta_call = mock_delta.call_args[1]
            assert delta_call["base_path"] == Path("custom/silver")

            gold_call = mock_gold.call_args[1]
            assert gold_call["base_path"] == Path("custom/gold")

    def test_local_run_with_json_export(
        self,
        mock_settings,
        mock_config_with_exports,
        mock_logger,
        mock_metrics,
    ):
        """Test local run with JSON export enabled."""
        with (
            patch(
                "bioetl.composition.factories.storage_factory.BronzeWriter"
            ) as mock_bronze,
            patch("bioetl.composition.factories.storage_factory.SilverWriter"),
            patch("bioetl.composition.factories.storage_factory.GoldWriter"),
        ):
            StorageFactory.create(
                settings=mock_settings,
                config=mock_config_with_exports,
                logger=mock_logger,
                metrics=mock_metrics,
            )

            # Verify BronzeWriter was called with save_json
            mock_bronze.assert_called_once()
            call_kwargs = mock_bronze.call_args[1]
            assert call_kwargs["save_json"] is True

    def test_local_run_with_csv_exports(
        self,
        mock_settings,
        mock_config_with_exports,
        mock_logger,
        mock_metrics,
    ):
        """Test local run with CSV export enabled for Silver and Gold."""
        from bioetl.infrastructure.export.csv_exporter import CsvExporter

        with (
            patch("bioetl.composition.factories.storage_factory.BronzeWriter"),
            patch(
                "bioetl.composition.factories.storage_factory.SilverWriter"
            ) as mock_delta,
            patch(
                "bioetl.composition.factories.storage_factory.GoldWriter"
            ) as mock_gold,
        ):
            StorageFactory.create(
                settings=mock_settings,
                config=mock_config_with_exports,
                logger=mock_logger,
                metrics=mock_metrics,
            )

            # Verify DeltaWriter (Silver) was called with csv_exporter
            mock_delta.assert_called_once()
            silver_call_kwargs = mock_delta.call_args[1]
            assert "csv_exporter" in silver_call_kwargs
            silver_exporter = silver_call_kwargs["csv_exporter"]
            assert isinstance(silver_exporter, CsvExporter)
            assert silver_exporter.base_path == Path("data/export/silver.csv")
            assert silver_exporter.delimiter == ","

            # Verify GoldWriter was called with csv_exporter
            mock_gold.assert_called_once()
            gold_call_kwargs = mock_gold.call_args[1]
            assert "csv_exporter" in gold_call_kwargs
            gold_exporter = gold_call_kwargs["csv_exporter"]
            assert isinstance(gold_exporter, CsvExporter)
            assert gold_exporter.base_path == Path("data/export/gold.csv")
            assert gold_exporter.delimiter == ";"


@pytest.mark.unit
class TestStorageFactoryEdgeCases:
    """Edge case tests for StorageFactory."""

    def test_empty_sink_config(
        self,
        mock_settings,
        mock_config_empty_sink,
        mock_logger,
        mock_metrics,
    ):
        """Test handling of empty sink configuration."""
        with (
            patch(
                "bioetl.composition.factories.storage_factory.BronzeWriter"
            ) as mock_bronze,
            patch("bioetl.composition.factories.storage_factory.SilverWriter"),
            patch("bioetl.composition.factories.storage_factory.GoldWriter"),
        ):
            result = StorageFactory.create(
                settings=mock_settings,
                config=mock_config_empty_sink,
                logger=mock_logger,
                metrics=mock_metrics,
            )

            # Should still create context with default settings
            assert isinstance(result, StorageContext)
            # BronzeWriter should be called with save_json=False
            mock_bronze.assert_called_once()
            call_kwargs = mock_bronze.call_args[1]
            assert call_kwargs["save_json"] is False

    def test_adapter_is_properly_composed(
        self,
        mock_settings,
        mock_config_minimal,
        mock_logger,
        mock_metrics,
    ):
        """Test that adapter contains all three writers."""
        bronze_instance = MagicMock()
        silver_instance = MagicMock()
        gold_instance = MagicMock()

        with (
            patch(
                "bioetl.composition.factories.storage_factory.BronzeWriter"
            ) as mock_bronze,
            patch(
                "bioetl.composition.factories.storage_factory.SilverWriter"
            ) as mock_delta,
            patch(
                "bioetl.composition.factories.storage_factory.GoldWriter"
            ) as mock_gold,
        ):
            mock_bronze.return_value = bronze_instance
            mock_delta.return_value = silver_instance
            mock_gold.return_value = gold_instance

            result = StorageFactory.create(
                settings=mock_settings,
                config=mock_config_minimal,
                logger=mock_logger,
                metrics=mock_metrics,
            )

            assert result.adapter.bronze is bronze_instance
            assert result.adapter.silver is silver_instance
            assert result.adapter.gold is gold_instance


@pytest.mark.unit
class TestStorageAdapterHealthCheck:
    """Tests for StorageAdapter.health_check() method."""

    @pytest.fixture
    def mock_bronze_writer(self, tmp_path):
        """Create mock bronze writer."""
        writer = MagicMock()
        writer.base_path = str(tmp_path / "bronze")
        return writer

    @pytest.fixture
    def mock_silver_writer(self, tmp_path):
        """Create mock silver writer."""
        writer = MagicMock()
        writer.base_path = str(tmp_path / "silver")
        writer.csv_exporter = None
        return writer

    @pytest.fixture
    def mock_gold_writer(self, tmp_path):
        """Create mock gold writer."""
        writer = MagicMock()
        writer.base_path = str(tmp_path / "gold")
        writer.csv_exporter = None
        return writer

    @pytest.mark.asyncio
    async def test_health_check_healthy_all_layers_writable(
        self, mock_bronze_writer, mock_silver_writer, mock_gold_writer, tmp_path
    ):
        """Test health check returns HEALTHY when all layers are writable."""
        from bioetl.domain.types import HealthStatus

        adapter = StorageAdapter(
            bronze_writer=mock_bronze_writer,
            silver_writer=mock_silver_writer,
            gold_writer=mock_gold_writer,
        )

        result = await adapter.health_check()

        assert result == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_degraded_partial_access(
        self, mock_bronze_writer, mock_silver_writer, mock_gold_writer
    ):
        """Test health check returns DEGRADED when some layers are not writable."""
        from unittest.mock import patch

        from bioetl.domain.types import HealthStatus

        adapter = StorageAdapter(
            bronze_writer=mock_bronze_writer,
            silver_writer=mock_silver_writer,
            gold_writer=mock_gold_writer,
        )

        # Mock _check_directory_writable to return False for gold path
        original_check = StorageAdapter._check_directory_writable

        def mock_check(path):
            if "gold" in str(path):
                return False
            return original_check(path)

        with patch.object(
            StorageAdapter, "_check_directory_writable", side_effect=mock_check
        ):
            result = await adapter.health_check()

        # DEGRADED because gold layer is not writable but bronze/silver are
        assert result == HealthStatus.DEGRADED

    def test_check_directory_writable_creates_probe_file(self, tmp_path):
        """Test _check_directory_writable creates and deletes probe file."""
        adapter = StorageAdapter(
            bronze_writer=MagicMock(),
            silver_writer=MagicMock(),
            gold_writer=MagicMock(),
        )

        result = adapter._check_directory_writable(tmp_path)

        assert result is True
        # Probe file should be cleaned up
        probe_file = tmp_path / ".health_check_probe"
        assert not probe_file.exists()


@pytest.mark.unit
class TestStorageAdapterClearOperations:
    """Tests for StorageAdapter clear operations."""

    @pytest.fixture
    def mock_bronze_writer(self, tmp_path):
        """Create mock bronze writer."""
        writer = MagicMock()
        writer.base_path = str(tmp_path / "bronze")
        return writer

    @pytest.fixture
    def mock_silver_writer(self, tmp_path):
        """Create mock silver writer."""
        writer = MagicMock()
        writer.base_path = str(tmp_path / "silver")
        writer.csv_exporter = None
        writer.clear = MagicMock(return_value=1)
        return writer

    @pytest.fixture
    def mock_gold_writer(self, tmp_path):
        """Create mock gold writer."""
        writer = MagicMock()
        writer.base_path = str(tmp_path / "gold")
        writer.csv_exporter = None
        writer.clear = MagicMock(return_value=1)
        return writer

    @pytest.mark.asyncio
    async def test_clear_silver_calls_writer(
        self, mock_bronze_writer, mock_silver_writer, mock_gold_writer
    ):
        """Test clear_silver delegates to silver writer."""
        adapter = StorageAdapter(
            bronze_writer=mock_bronze_writer,
            silver_writer=mock_silver_writer,
            gold_writer=mock_gold_writer,
        )

        result = await adapter.clear_silver("chembl_activity", dry_run=False)

        assert result == 1
        mock_silver_writer.clear.assert_called_once_with(
            "chembl_activity", dry_run=False
        )

    @pytest.mark.asyncio
    async def test_clear_gold_calls_writer(
        self, mock_bronze_writer, mock_silver_writer, mock_gold_writer
    ):
        """Test clear_gold delegates to gold writer."""
        adapter = StorageAdapter(
            bronze_writer=mock_bronze_writer,
            silver_writer=mock_silver_writer,
            gold_writer=mock_gold_writer,
        )

        result = await adapter.clear_gold("chembl_activity", dry_run=False)

        assert result == 1
        mock_gold_writer.clear.assert_called_once_with("chembl_activity", dry_run=False)


@pytest.mark.unit
class TestStorageAdapterPreviewCleanup:
    """Tests for StorageAdapter.preview_cleanup() method."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage structure."""
        silver_path = tmp_path / "silver" / "chembl" / "activity"
        gold_path = tmp_path / "gold" / "chembl" / "activity"
        silver_path.mkdir(parents=True)
        gold_path.mkdir(parents=True)

        # Create some test files
        (silver_path / "file1.parquet").touch()
        (silver_path / "file2.parquet").touch()
        (gold_path / "file1.parquet").touch()

        return tmp_path

    @pytest.fixture
    def adapter_with_temp_storage(self, temp_storage):
        """Create adapter with temp storage."""
        from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter
        from bioetl.infrastructure.storage.gold_writer import GoldWriter

        bronze = MagicMock(spec=BronzeWriter)
        bronze.base_path = str(temp_storage / "bronze")

        silver = MagicMock(spec=DeltaWriter)
        silver.base_path = str(temp_storage / "silver")
        silver.get_table_path = MagicMock(
            return_value=temp_storage / "silver" / "chembl" / "activity"
        )

        gold = MagicMock(spec=GoldWriter)
        gold.base_path = str(temp_storage / "gold")
        gold.get_table_path = MagicMock(
            return_value=temp_storage / "gold" / "chembl" / "activity"
        )

        return StorageAdapter(
            bronze_writer=bronze,
            silver_writer=silver,
            gold_writer=gold,
        )

    def test_preview_cleanup_returns_file_counts(
        self, adapter_with_temp_storage, temp_storage
    ):
        """Test preview_cleanup returns correct file counts."""
        result = adapter_with_temp_storage.preview_cleanup(
            silver_table="chembl.activity",
            gold_table="chembl.activity",
        )

        assert result["silver"]["file_count"] == 2
        assert result["silver"]["exists"] is True
        assert result["gold"]["file_count"] == 1
        assert result["gold"]["exists"] is True
        assert result["total_files"] == 3

    def test_preview_cleanup_without_gold(self, adapter_with_temp_storage):
        """Test preview_cleanup when gold_table is not specified."""
        result = adapter_with_temp_storage.preview_cleanup(
            silver_table="chembl.activity",
            gold_table=None,
        )

        assert result["silver"]["file_count"] == 2
        assert result["gold"] is None
        assert result["total_files"] == 2


@pytest.mark.unit
class TestStorageAdapterVacuum:
    """Tests for StorageAdapter.vacuum() method."""

    @pytest.fixture
    def mock_writers(self, tmp_path):
        """Create mock writers."""
        bronze = MagicMock()
        bronze.base_path = str(tmp_path / "bronze")

        silver = MagicMock()
        silver.base_path = str(tmp_path / "silver")
        silver.vacuum = MagicMock(return_value=["file1", "file2"])

        gold = MagicMock()
        gold.base_path = str(tmp_path / "gold")

        return bronze, silver, gold

    @pytest.mark.asyncio
    async def test_vacuum_calls_silver_vacuum(self, mock_writers):
        """Test vacuum delegates to silver writer."""
        bronze, silver, gold = mock_writers

        adapter = StorageAdapter(
            bronze_writer=bronze,
            silver_writer=silver,
            gold_writer=gold,
        )

        # Mock the silver.vacuum as async
        async def mock_vacuum(**kwargs):
            return ["file1", "file2"]

        silver.vacuum = mock_vacuum

        result = await adapter.vacuum("chembl_activity", retention_hours=168)

        # Should have vacuumed at least silver (2 files)
        assert result >= 2


@pytest.mark.unit
class TestStorageAdapterAclose:
    """Tests for StorageAdapter.aclose() method."""

    @pytest.mark.asyncio
    async def test_aclose_completes_without_error(self):
        """Test aclose completes without raising."""
        adapter = StorageAdapter(
            bronze_writer=MagicMock(),
            silver_writer=MagicMock(),
            gold_writer=MagicMock(),
        )

        # Should not raise
        await adapter.aclose()

    @pytest.mark.asyncio
    async def test_aclose_is_idempotent(self):
        """Test aclose can be called multiple times."""
        adapter = StorageAdapter(
            bronze_writer=MagicMock(),
            silver_writer=MagicMock(),
            gold_writer=MagicMock(),
        )

        # Should not raise on multiple calls
        await adapter.aclose()
        await adapter.aclose()
