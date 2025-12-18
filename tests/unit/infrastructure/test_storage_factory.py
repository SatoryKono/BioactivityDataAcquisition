"""Unit tests for StorageFactory."""

from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.factories.storage_factory import StorageContext, StorageFactory
from bioetl.infrastructure.factories.storage import StorageAdapter
from bioetl.infrastructure.config import Settings


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

    @patch("bioetl.infrastructure.factories.storage_factory.BronzeWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.DeltaWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.GoldWriter")
    def test_local_run_uses_data_output_paths(
        self,
        mock_gold_writer,
        mock_delta_writer,
        mock_bronze_writer,
        mock_settings_local,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that local runs use data/output paths."""
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

    @patch("bioetl.infrastructure.factories.storage_factory.BronzeWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.DeltaWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.GoldWriter")
    def test_local_run_with_json_export(
        self,
        mock_gold_writer,
        mock_delta_writer,
        mock_bronze_writer,
        mock_settings_local,
        mock_config_with_exports,
        mock_logger,
    ):
        """Test local run with JSON export enabled."""
        StorageFactory.create(
            settings=mock_settings_local,
            config=mock_config_with_exports,
            logger=mock_logger,
        )

        # Verify BronzeWriter was called with json_path
        mock_bronze_writer.assert_called_once()
        call_kwargs = mock_bronze_writer.call_args[1]
        assert call_kwargs["save_json"] is True
        assert call_kwargs["json_path"] == "data/output/json"

    @patch("bioetl.infrastructure.factories.storage_factory.BronzeWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.DeltaWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.GoldWriter")
    def test_local_run_with_csv_exports(
        self,
        mock_gold_writer,
        mock_delta_writer,
        mock_bronze_writer,
        mock_settings_local,
        mock_config_with_exports,
        mock_logger,
    ):
        """Test local run with CSV export enabled for Silver and Gold."""
        StorageFactory.create(
            settings=mock_settings_local,
            config=mock_config_with_exports,
            logger=mock_logger,
        )

        # Verify DeltaWriter (Silver) was called with csv options
        mock_delta_writer.assert_called_once()
        silver_call_kwargs = mock_delta_writer.call_args[1]
        assert silver_call_kwargs["csv_path"] == "data/export/silver.csv"
        assert silver_call_kwargs["csv_options"]["delimiter"] == ","

        # Verify GoldWriter was called with csv options
        mock_gold_writer.assert_called_once()
        gold_call_kwargs = mock_gold_writer.call_args[1]
        assert gold_call_kwargs["csv_path"] == "data/export/gold.csv"
        assert gold_call_kwargs["csv_options"]["delimiter"] == ";"

    @patch("bioetl.infrastructure.factories.storage_factory.BronzeWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.DeltaWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.GoldWriter")
    def test_local_run_logs_info(
        self,
        mock_gold_writer,
        mock_delta_writer,
        mock_bronze_writer,
        mock_settings_local,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that local run logs appropriate info message."""
        StorageFactory.create(
            settings=mock_settings_local,
            config=mock_config_minimal,
            logger=mock_logger,
        )

        mock_logger.info.assert_called()
        # Find the call with "Local run detected"
        local_run_calls = [
            call for call in mock_logger.info.call_args_list
            if "Local run detected" in str(call)
        ]
        assert len(local_run_calls) >= 1


@pytest.mark.unit
class TestStorageFactoryCloud:
    """Tests for StorageFactory.create() in cloud mode."""

    @patch("bioetl.infrastructure.factories.storage_factory.BronzeWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.DeltaWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.GoldWriter")
    def test_cloud_run_uses_s3_paths(
        self,
        mock_gold_writer,
        mock_delta_writer,
        mock_bronze_writer,
        mock_settings_cloud,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that cloud runs use S3 bucket paths."""
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

    @patch("bioetl.infrastructure.factories.storage_factory.BronzeWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.DeltaWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.GoldWriter")
    def test_cloud_run_uses_endpoint_url(
        self,
        mock_gold_writer,
        mock_delta_writer,
        mock_bronze_writer,
        mock_settings_cloud,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that cloud runs pass endpoint_url to BronzeWriter."""
        StorageFactory.create(
            settings=mock_settings_cloud,
            config=mock_config_minimal,
            logger=mock_logger,
        )

        mock_bronze_writer.assert_called_once()
        call_kwargs = mock_bronze_writer.call_args[1]
        assert call_kwargs["endpoint_url"] == "https://s3.amazonaws.com"

    @patch("bioetl.infrastructure.factories.storage_factory.BronzeWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.DeltaWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.GoldWriter")
    def test_cloud_run_uses_storage_options(
        self,
        mock_gold_writer,
        mock_delta_writer,
        mock_bronze_writer,
        mock_settings_cloud,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that cloud runs pass storage_options to writers."""
        StorageFactory.create(
            settings=mock_settings_cloud,
            config=mock_config_minimal,
            logger=mock_logger,
        )

        # DeltaWriter should receive storage_options
        mock_delta_writer.assert_called_once()
        delta_kwargs = mock_delta_writer.call_args[1]
        assert delta_kwargs["storage_options"] == {"AWS_ACCESS_KEY_ID": "prod_key"}

        # GoldWriter should receive storage_options
        mock_gold_writer.assert_called_once()
        gold_kwargs = mock_gold_writer.call_args[1]
        assert gold_kwargs["storage_options"] == {"AWS_ACCESS_KEY_ID": "prod_key"}


@pytest.mark.unit
class TestStorageFactoryEdgeCases:
    """Edge case tests for StorageFactory."""

    @patch("bioetl.infrastructure.factories.storage_factory.BronzeWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.DeltaWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.GoldWriter")
    def test_empty_sink_config(
        self,
        mock_gold_writer,
        mock_delta_writer,
        mock_bronze_writer,
        mock_settings_local,
        mock_config_empty_sink,
        mock_logger,
    ):
        """Test handling of empty sink configuration."""
        result = StorageFactory.create(
            settings=mock_settings_local,
            config=mock_config_empty_sink,
            logger=mock_logger,
        )

        # Should still create context with default settings
        assert isinstance(result, StorageContext)
        # BronzeWriter should be called with save_json=False
        mock_bronze_writer.assert_called_once()
        call_kwargs = mock_bronze_writer.call_args[1]
        assert call_kwargs["save_json"] is False

    @patch("bioetl.infrastructure.factories.storage_factory.BronzeWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.DeltaWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.GoldWriter")
    def test_dev_env_with_endpoint_url_is_cloud(
        self,
        mock_gold_writer,
        mock_delta_writer,
        mock_bronze_writer,
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

        result = StorageFactory.create(
            settings=settings,
            config=mock_config_minimal,
            logger=mock_logger,
        )

        # Should use S3 paths because endpoint_url is set
        assert result.bronze_path == "dev-bronze"
        assert result.silver_path == "s3://dev-silver"
        assert result.gold_path == "s3://dev-gold"

    @patch("bioetl.infrastructure.factories.storage_factory.BronzeWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.DeltaWriter")
    @patch("bioetl.infrastructure.factories.storage_factory.GoldWriter")
    def test_adapter_is_properly_composed(
        self,
        mock_gold_writer,
        mock_delta_writer,
        mock_bronze_writer,
        mock_settings_local,
        mock_config_minimal,
        mock_logger,
    ):
        """Test that adapter contains all three writers."""
        bronze_instance = MagicMock()
        silver_instance = MagicMock()
        gold_instance = MagicMock()

        mock_bronze_writer.return_value = bronze_instance
        mock_delta_writer.return_value = silver_instance
        mock_gold_writer.return_value = gold_instance

        result = StorageFactory.create(
            settings=mock_settings_local,
            config=mock_config_minimal,
            logger=mock_logger,
        )

        assert result.adapter.bronze is bronze_instance
        assert result.adapter.silver is silver_instance
        assert result.adapter.gold is gold_instance
