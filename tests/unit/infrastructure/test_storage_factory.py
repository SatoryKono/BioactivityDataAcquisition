"""Unit tests for StorageFactory."""

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.storage_factory import (
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
def mock_settings_local():
    """Settings for local run (non-prod, no endpoint_url)."""
    settings = MagicMock()
    settings.env = "dev"
    settings.aws.endpoint_url = None
    settings.aws.access_key = "test_key"
    settings.aws.secret_key = "test_secret"
    settings.s3.bucket_bronze = "prod-bronze"
    settings.s3.bucket_silver = "prod-silver"
    settings.s3.bucket_gold = "prod-gold"
    settings.s3.bucket_checkpoints = "prod-checkpoints"
    settings.storage_options = {"AWS_ACCESS_KEY_ID": "test"}
    return settings


@pytest.fixture
def mock_settings_cloud():
    """Settings for cloud run (prod with endpoint_url)."""
    settings = MagicMock()
    settings.env = "prod"
    settings.aws.endpoint_url = "https://s3.amazonaws.com"
    settings.aws.access_key = "prod_key"
    settings.aws.secret_key = "prod_secret"
    settings.s3.bucket_bronze = "prod-bronze-bucket"
    settings.s3.bucket_silver = "prod-silver-bucket"
    settings.s3.bucket_gold = "prod-gold-bucket"
    settings.s3.bucket_checkpoints = "prod-checkpoints-bucket"
    settings.storage_options = {"AWS_ACCESS_KEY_ID": "prod_key"}
    return settings


@pytest.fixture
def mock_config_minimal():
    """Minimal pipeline config without export options."""
    config = MagicMock()
    config.sink = {
        "bronze": MagicMock(save_json=False),
        "silver": MagicMock(csv_export=MagicMock(enabled=False)),
        "gold": MagicMock(csv_export=MagicMock(enabled=False)),
    }
    return config


@pytest.fixture
def mock_config_with_exports():
    """Pipeline config with CSV and JSON exports enabled."""
    config = MagicMock()

    bronze_config = MagicMock()
    bronze_config.save_json = True

    silver_csv = MagicMock()
    silver_csv.enabled = True
    silver_csv.path = "data/export/silver.csv"
    silver_csv.delimiter = ","
    silver_csv.header = True
    silver_csv.encoding = "utf-8"

    silver_config = MagicMock()
    silver_config.csv_export = silver_csv

    gold_csv = MagicMock()
    gold_csv.enabled = True
    gold_csv.path = "data/export/gold.csv"
    gold_csv.delimiter = ";"
    gold_csv.header = True
    gold_csv.encoding = "utf-8"

    gold_config = MagicMock()
    gold_config.csv_export = gold_csv

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
            bronze_path="/path/to/bronze",
            silver_path="/path/to/silver",
            gold_path="/path/to/gold",
            checkpoints_path="/path/to/checkpoints",
        )

        assert context.adapter is adapter
        assert context.bronze_path == "/path/to/bronze"
        assert context.silver_path == "/path/to/silver"
        assert context.gold_path == "/path/to/gold"
        assert context.checkpoints_path == "/path/to/checkpoints"

    def test_storage_context_is_frozen(self, mock_logger):
        """Test StorageContext is immutable."""
        adapter = MagicMock(spec=StorageAdapter)
        context = StorageContext(
            adapter=adapter,
            bronze_path="/path/to/bronze",
            silver_path="/path/to/silver",
            gold_path="/path/to/gold",
            checkpoints_path="/path/to/checkpoints",
        )

        with pytest.raises(AttributeError):
            context.bronze_path = "/new/path"


@pytest.mark.unit
class TestStorageFactoryLocal:
    """Tests for StorageFactory.create() in local mode."""

    def test_local_run_uses_data_output_paths(
        self,
        mock_settings_local,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that local runs use data/output paths."""
        with (
            patch("bioetl.composition.factories.storage_factory.BronzeWriter"),
            patch("bioetl.composition.factories.storage_factory.DeltaWriter"),
            patch("bioetl.composition.factories.storage_factory.GoldWriter"),
        ):
            result = StorageFactory.create(
                settings=mock_settings_local,
                config=mock_config_minimal,
                logger=mock_logger,
            )

            assert isinstance(result, StorageContext)
            assert result.bronze_path == "data/output/bronze"
            assert result.silver_path == "data/output/silver"
            assert result.gold_path == "data/output/gold"
            assert result.checkpoints_path == "data/output/checkpoints"

    def test_local_run_with_json_export(
        self,
        mock_settings_local,
        mock_config_with_exports,
        mock_logger,
    ):
        """Test local run with JSON export enabled."""
        with (
            patch(
                "bioetl.composition.factories.storage_factory.BronzeWriter"
            ) as mock_bronze,
            patch("bioetl.composition.factories.storage_factory.DeltaWriter"),
            patch("bioetl.composition.factories.storage_factory.GoldWriter"),
        ):
            StorageFactory.create(
                settings=mock_settings_local,
                config=mock_config_with_exports,
                logger=mock_logger,
            )

            # Verify BronzeWriter was called with json_path
            mock_bronze.assert_called_once()
            call_kwargs = mock_bronze.call_args[1]
            assert call_kwargs["save_json"] is True
            assert call_kwargs["json_path"] == "data/output/json"

    def test_local_run_with_csv_exports(
        self,
        mock_settings_local,
        mock_config_with_exports,
        mock_logger,
    ):
        """Test local run with CSV export enabled for Silver and Gold."""
        from pathlib import Path

        from bioetl.infrastructure.export.csv_exporter import CsvExporter

        with (
            patch("bioetl.composition.factories.storage_factory.BronzeWriter"),
            patch(
                "bioetl.composition.factories.storage_factory.DeltaWriter"
            ) as mock_delta,
            patch(
                "bioetl.composition.factories.storage_factory.GoldWriter"
            ) as mock_gold,
        ):
            StorageFactory.create(
                settings=mock_settings_local,
                config=mock_config_with_exports,
                logger=mock_logger,
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

    def test_local_run_logs_info(
        self,
        mock_settings_local,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that local run logs appropriate info message."""
        with (
            patch("bioetl.composition.factories.storage_factory.BronzeWriter"),
            patch("bioetl.composition.factories.storage_factory.DeltaWriter"),
            patch("bioetl.composition.factories.storage_factory.GoldWriter"),
        ):
            StorageFactory.create(
                settings=mock_settings_local,
                config=mock_config_minimal,
                logger=mock_logger,
            )

            mock_logger.info.assert_called()
            # Find the call with "Local run detected"
            local_run_calls = [
                call
                for call in mock_logger.info.call_args_list
                if "Local run detected" in str(call)
            ]
            assert len(local_run_calls) >= 1


@pytest.mark.unit
class TestStorageFactoryCloud:
    """Tests for StorageFactory.create() in cloud mode."""

    def test_cloud_run_uses_s3_paths(
        self,
        mock_settings_cloud,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that cloud runs use S3 bucket paths."""
        with (
            patch("bioetl.composition.factories.storage_factory.BronzeWriter"),
            patch("bioetl.composition.factories.storage_factory.DeltaWriter"),
            patch("bioetl.composition.factories.storage_factory.GoldWriter"),
        ):
            result = StorageFactory.create(
                settings=mock_settings_cloud,
                config=mock_config_minimal,
                logger=mock_logger,
            )

            assert isinstance(result, StorageContext)
            assert result.bronze_path == "prod-bronze-bucket"
            assert result.silver_path == "s3://prod-silver-bucket"
            assert result.gold_path == "s3://prod-gold-bucket"
            assert result.checkpoints_path == "prod-checkpoints-bucket"

    def test_cloud_run_uses_endpoint_url(
        self,
        mock_settings_cloud,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that cloud runs pass endpoint_url to BronzeWriter."""
        with (
            patch(
                "bioetl.composition.factories.storage_factory.BronzeWriter"
            ) as mock_bronze,
            patch("bioetl.composition.factories.storage_factory.DeltaWriter"),
            patch("bioetl.composition.factories.storage_factory.GoldWriter"),
        ):
            StorageFactory.create(
                settings=mock_settings_cloud,
                config=mock_config_minimal,
                logger=mock_logger,
            )

            mock_bronze.assert_called_once()
            call_kwargs = mock_bronze.call_args[1]
            assert call_kwargs["endpoint_url"] == "https://s3.amazonaws.com"

    def test_cloud_run_uses_storage_options(
        self,
        mock_settings_cloud,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that cloud runs pass storage_options to writers."""
        with (
            patch("bioetl.composition.factories.storage_factory.BronzeWriter"),
            patch(
                "bioetl.composition.factories.storage_factory.DeltaWriter"
            ) as mock_delta,
            patch(
                "bioetl.composition.factories.storage_factory.GoldWriter"
            ) as mock_gold,
        ):
            StorageFactory.create(
                settings=mock_settings_cloud,
                config=mock_config_minimal,
                logger=mock_logger,
            )

            # DeltaWriter should receive storage_options
            mock_delta.assert_called_once()
            delta_kwargs = mock_delta.call_args[1]
            assert delta_kwargs["storage_options"] == {"AWS_ACCESS_KEY_ID": "prod_key"}

            # GoldWriter should receive storage_options
            mock_gold.assert_called_once()
            gold_kwargs = mock_gold.call_args[1]
            assert gold_kwargs["storage_options"] == {"AWS_ACCESS_KEY_ID": "prod_key"}


@pytest.mark.unit
class TestStorageFactoryEdgeCases:
    """Edge case tests for StorageFactory."""

    def test_empty_sink_config(
        self,
        mock_settings_local,
        mock_config_empty_sink,
        mock_logger,
    ):
        """Test handling of empty sink configuration."""
        with (
            patch(
                "bioetl.composition.factories.storage_factory.BronzeWriter"
            ) as mock_bronze,
            patch("bioetl.composition.factories.storage_factory.DeltaWriter"),
            patch("bioetl.composition.factories.storage_factory.GoldWriter"),
        ):
            result = StorageFactory.create(
                settings=mock_settings_local,
                config=mock_config_empty_sink,
                logger=mock_logger,
            )

            # Should still create context with default settings
            assert isinstance(result, StorageContext)
            # BronzeWriter should be called with save_json=False
            mock_bronze.assert_called_once()
            call_kwargs = mock_bronze.call_args[1]
            assert call_kwargs["save_json"] is False

    def test_dev_env_with_endpoint_url_is_cloud(
        self,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that dev env with endpoint_url is treated as cloud."""
        settings = MagicMock()
        settings.env = "dev"  # Not prod
        settings.aws.endpoint_url = "http://localhost:4566"  # But has endpoint
        settings.aws.access_key = "test"
        settings.aws.secret_key = "test"
        settings.s3.bucket_bronze = "dev-bronze"
        settings.s3.bucket_silver = "dev-silver"
        settings.s3.bucket_gold = "dev-gold"
        settings.s3.bucket_checkpoints = "dev-checkpoints"
        settings.storage_options = {}

        with (
            patch("bioetl.composition.factories.storage_factory.BronzeWriter"),
            patch("bioetl.composition.factories.storage_factory.DeltaWriter"),
            patch("bioetl.composition.factories.storage_factory.GoldWriter"),
        ):
            result = StorageFactory.create(
                settings=settings,
                config=mock_config_minimal,
                logger=mock_logger,
            )

            # Should use S3 paths because endpoint_url is set
            assert result.bronze_path == "dev-bronze"
            assert result.silver_path == "s3://dev-silver"
            assert result.gold_path == "s3://dev-gold"

    def test_adapter_is_properly_composed(
        self,
        mock_settings_local,
        mock_config_minimal,
        mock_logger,
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
                "bioetl.composition.factories.storage_factory.DeltaWriter"
            ) as mock_delta,
            patch(
                "bioetl.composition.factories.storage_factory.GoldWriter"
            ) as mock_gold,
        ):
            mock_bronze.return_value = bronze_instance
            mock_delta.return_value = silver_instance
            mock_gold.return_value = gold_instance

            result = StorageFactory.create(
                settings=mock_settings_local,
                config=mock_config_minimal,
                logger=mock_logger,
            )

            assert result.adapter.bronze is bronze_instance
            assert result.adapter.silver is silver_instance
            assert result.adapter.gold is gold_instance
