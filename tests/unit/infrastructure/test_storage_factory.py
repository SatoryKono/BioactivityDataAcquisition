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
            patch("bioetl.composition.factories.storage_factory.DeltaWriter"),
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
            "silver": MagicMock(csv_export=MagicMock(enabled=False), path="custom/silver"),
            "gold": MagicMock(csv_export=MagicMock(enabled=False), path="custom/gold"),
        }
        mock_settings.test_mode = False

        with (
            patch("bioetl.composition.factories.storage_factory.BronzeWriter") as mock_bronze,
            patch("bioetl.composition.factories.storage_factory.DeltaWriter") as mock_delta,
            patch("bioetl.composition.factories.storage_factory.GoldWriter") as mock_gold,
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
            patch("bioetl.composition.factories.storage_factory.BronzeWriter") as mock_bronze,
            patch("bioetl.composition.factories.storage_factory.DeltaWriter"),
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
            patch("bioetl.composition.factories.storage_factory.DeltaWriter") as mock_delta,
            patch("bioetl.composition.factories.storage_factory.GoldWriter") as mock_gold,
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
            patch("bioetl.composition.factories.storage_factory.BronzeWriter") as mock_bronze,
            patch("bioetl.composition.factories.storage_factory.DeltaWriter"),
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
            patch("bioetl.composition.factories.storage_factory.BronzeWriter") as mock_bronze,
            patch("bioetl.composition.factories.storage_factory.DeltaWriter") as mock_delta,
            patch("bioetl.composition.factories.storage_factory.GoldWriter") as mock_gold,
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
