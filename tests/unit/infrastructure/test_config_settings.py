"""Unit tests for infrastructure config settings classes."""

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config import PipelineConfig
from bioetl.infrastructure.config import (
    AWSSettings,
    PipelineSettings,
    RedisSettings,
    S3Settings,
    Settings,
    get_settings,
    yaml_config_to_domain,
)


@pytest.mark.unit
class TestAWSSettings:
    """Tests for AWSSettings class."""

    def test_default_values(self, monkeypatch) -> None:
        """Test default AWS settings."""
        # Clear env vars that AWSSettings reads
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
        monkeypatch.delenv("BIOETL_AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("BIOETL_AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("BIOETL_AWS_ENDPOINT_URL", raising=False)

        settings = AWSSettings(_env_file=None)

        assert settings.access_key_id is None
        assert settings.secret_access_key is None
        assert settings.endpoint_url is None
        assert settings.default_region == "us-east-1"

    def test_region_property(self, monkeypatch) -> None:
        """Test region alias property."""
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.delenv("BIOETL_AWS_REGION", raising=False)
        monkeypatch.delenv("BIOETL_AWS_DEFAULT_REGION", raising=False)

        # Must use validation_alias name, not field name
        settings = AWSSettings(aws_default_region="eu-west-1", _env_file=None)

        assert settings.region == "eu-west-1"
        assert settings.region == settings.default_region

    def test_is_configured_false(self, monkeypatch) -> None:
        """Test is_configured returns False when credentials missing."""
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("BIOETL_AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("BIOETL_AWS_SECRET_ACCESS_KEY", raising=False)

        settings = AWSSettings(_env_file=None)
        assert settings.is_configured is False

        # Must use validation_alias name
        settings_partial = AWSSettings(aws_access_key_id="key", _env_file=None)
        assert settings_partial.is_configured is False

    def test_is_configured_true(self, monkeypatch) -> None:
        """Test is_configured returns True when credentials present."""
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("BIOETL_AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("BIOETL_AWS_SECRET_ACCESS_KEY", raising=False)
        # Must use validation_alias names, not field names
        settings = AWSSettings(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key=SecretStr("secret"),
            _env_file=None,
        )
        assert settings.is_configured is True

    def test_immutability(self) -> None:
        """Test that settings are frozen."""
        settings = AWSSettings(_env_file=None)

        with pytest.raises(Exception):  # ValidationError for frozen model
            settings.access_key_id = "new_key"


@pytest.mark.unit
class TestS3Settings:
    """Tests for S3Settings class."""

    def test_default_values(self) -> None:
        """Test default S3 bucket names."""
        settings = S3Settings()

        assert settings.bucket_bronze == "bioetl-bronze"
        assert settings.bucket_silver == "bioetl-silver"
        assert settings.bucket_gold == "bioetl-gold"
        assert settings.bucket_checkpoints == "bioetl-checkpoints"

    def test_custom_values(self) -> None:
        """Test custom S3 bucket names."""
        settings = S3Settings(
            bucket_bronze="my-bronze",
            bucket_silver="my-silver",
            bucket_gold="my-gold",
            bucket_checkpoints="my-checkpoints",
        )

        assert settings.bucket_bronze == "my-bronze"
        assert settings.bucket_silver == "my-silver"
        assert settings.bucket_gold == "my-gold"
        assert settings.bucket_checkpoints == "my-checkpoints"


@pytest.mark.unit
class TestRedisSettings:
    """Tests for RedisSettings class."""

    def test_default_values(self) -> None:
        """Test default Redis settings."""
        settings = RedisSettings()

        assert settings.host == "localhost"
        assert settings.port == 6379
        assert settings.password is None
        assert settings.db == 0

    def test_custom_values(self) -> None:
        """Test custom Redis settings."""
        settings = RedisSettings(
            host="redis.example.com",
            port=6380,
            password=SecretStr("secret"),
            db=1,
        )

        assert settings.host == "redis.example.com"
        assert settings.port == 6380
        assert settings.password.get_secret_value() == "secret"
        assert settings.db == 1

    def test_port_validation(self) -> None:
        """Test port validation boundaries."""
        # Valid boundary
        settings = RedisSettings(port=1)
        assert settings.port == 1

        settings = RedisSettings(port=65535)
        assert settings.port == 65535

        # Invalid
        with pytest.raises(Exception):
            RedisSettings(port=0)

        with pytest.raises(Exception):
            RedisSettings(port=65536)


@pytest.mark.unit
class TestPipelineSettings:
    """Tests for PipelineSettings class."""

    def test_default_values(self) -> None:
        """Test default pipeline settings."""
        settings = PipelineSettings()

        assert settings.batch_size == 100
        assert settings.checkpoint_interval == 1000
        assert settings.max_concurrent_batches == 4
        assert settings.heartbeat_interval == 20

    def test_custom_values(self) -> None:
        """Test custom pipeline settings."""
        settings = PipelineSettings(
            batch_size=500,
            checkpoint_interval=5000,
            max_concurrent_batches=8,
            heartbeat_interval=30,
        )

        assert settings.batch_size == 500
        assert settings.checkpoint_interval == 5000
        assert settings.max_concurrent_batches == 8
        assert settings.heartbeat_interval == 30

    def test_batch_size_validation(self) -> None:
        """Test batch_size validation."""
        # Valid
        settings = PipelineSettings(batch_size=1)
        assert settings.batch_size == 1

        settings = PipelineSettings(batch_size=10000)
        assert settings.batch_size == 10000

        # Invalid
        with pytest.raises(Exception):
            PipelineSettings(batch_size=0)

        with pytest.raises(Exception):
            PipelineSettings(batch_size=10001)

    def test_heartbeat_interval_validation(self) -> None:
        """Test heartbeat_interval validation."""
        # Valid boundaries
        settings = PipelineSettings(heartbeat_interval=5)
        assert settings.heartbeat_interval == 5

        settings = PipelineSettings(heartbeat_interval=60)
        assert settings.heartbeat_interval == 60

        # Invalid
        with pytest.raises(Exception):
            PipelineSettings(heartbeat_interval=4)

        with pytest.raises(Exception):
            PipelineSettings(heartbeat_interval=61)


@pytest.mark.unit
class TestSettings:
    """Tests for main Settings class."""

    def test_default_values(self, monkeypatch) -> None:
        """Test default main settings."""
        # Clear BIOETL_ENV to test explicit values
        monkeypatch.delenv("BIOETL_ENV", raising=False)
        # Use test_mode to bypass dev validation, explicitly set env
        settings = Settings(test_mode=True, env="dev")

        assert settings.env == "dev"
        assert settings.debug is False
        assert settings.test_mode is True
        assert settings.strict_error_handling is False

    def test_nested_settings(self) -> None:
        """Test nested settings objects."""
        settings = Settings(test_mode=True, _env_file=None)

        assert isinstance(settings.aws, AWSSettings)
        assert isinstance(settings.s3, S3Settings)
        assert isinstance(settings.redis, RedisSettings)
        assert isinstance(settings.pipeline, PipelineSettings)

    def test_storage_options_none(self, monkeypatch) -> None:
        """Test storage_options returns None without endpoint."""
        # Clear AWS env vars to ensure no endpoint is set
        monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
        monkeypatch.delenv("BIOETL_AWS_ENDPOINT_URL", raising=False)

        aws = AWSSettings(_env_file=None)
        settings = Settings(aws=aws, test_mode=True, _env_file=None)
        assert settings.storage_options is None

    def test_storage_options_with_endpoint(self, monkeypatch) -> None:
        """Test storage_options with endpoint configured."""
        monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
        monkeypatch.delenv("BIOETL_AWS_ENDPOINT_URL", raising=False)
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("BIOETL_AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("BIOETL_AWS_SECRET_ACCESS_KEY", raising=False)

        # Must use validation_alias names, not field names
        aws = AWSSettings(
            aws_endpoint_url="http://localhost:9000",
            aws_access_key_id="access",
            aws_secret_access_key=SecretStr("secret"),
            _env_file=None,
        )
        settings = Settings(aws=aws, test_mode=True, _env_file=None)

        options = settings.storage_options
        assert options is not None
        assert options["AWS_ENDPOINT_URL"] == "http://localhost:9000"
        assert options["AWS_ACCESS_KEY_ID"] == "access"
        assert options["AWS_SECRET_ACCESS_KEY"] == "secret"

    def test_dev_env_allows_no_endpoint(self, monkeypatch) -> None:
        """Test that dev env allows no endpoint_url (uses local storage)."""
        # Clear all AWS env vars to ensure no endpoint is set
        monkeypatch.delenv("BIOETL_ENV", raising=False)
        monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
        monkeypatch.delenv("BIOETL_AWS_ENDPOINT_URL", raising=False)

        get_settings.cache_clear()

        aws = AWSSettings(_env_file=None)
        # Dev without endpoint_url is allowed (local storage mode)
        settings = Settings(env="dev", test_mode=False, aws=aws, _env_file=None)
        assert settings.env == "dev"
        assert settings.storage_options is None  # No S3 storage configured

    def test_staging_env_no_endpoint_required(self, monkeypatch) -> None:
        """Test that staging env doesn't require endpoint."""
        monkeypatch.setenv("BIOETL_ENV", "staging")
        get_settings.cache_clear()
        settings = Settings()
        assert settings.env == "staging"

    def test_prod_env_no_endpoint_required(self, monkeypatch) -> None:
        """Test that prod env doesn't require endpoint."""
        monkeypatch.setenv("BIOETL_ENV", "prod")
        get_settings.cache_clear()
        settings = Settings()
        assert settings.env == "prod"


@pytest.mark.unit
class TestYamlConfigToDomain:
    """Tests for yaml_config_to_domain function."""

    def test_basic_mapping(self) -> None:
        """Test basic config mapping."""
        yaml_config = MagicMock()
        yaml_config.pipeline_name = "test_pipeline"
        yaml_config.provider = "test"
        yaml_config.entity_type = "entity"
        yaml_config.primary_keys = ["id"]
        yaml_config.silver_table = "silver_table"
        yaml_config.gold_table = "gold_table"
        yaml_config.gold_filter_types = None
        yaml_config.batch_size = 200
        yaml_config.checkpoint_interval = 2000
        yaml_config.source = MagicMock()
        yaml_config.source.fields = []
        yaml_config.source.watermark_field = None
        yaml_config.dq_rules = MagicMock()
        yaml_config.dq_rules.soft_fail_threshold = 0.05
        yaml_config.dq_rules.hard_fail_threshold = 0.20

        result = yaml_config_to_domain(yaml_config)

        assert isinstance(result, PipelineConfig)
        assert result.pipeline_name == "test_pipeline"
        assert result.provider == "test"
        assert result.entity_type == "entity"
        assert result.primary_keys == ["id"]
        assert result.silver_table == "silver_table"
        assert result.gold_table == "gold_table"
        assert result.batch_size == 200
        assert result.checkpoint_interval == 2000

    def test_fields_extraction(self) -> None:
        """Test field names extraction from source config."""
        yaml_config = MagicMock()
        yaml_config.pipeline_name = "test"
        yaml_config.provider = "test"
        yaml_config.entity_type = "test"
        yaml_config.primary_keys = ["id"]
        yaml_config.silver_table = "silver"
        yaml_config.gold_table = None
        yaml_config.gold_filter_types = None
        yaml_config.batch_size = 100
        yaml_config.checkpoint_interval = 1000
        yaml_config.source = MagicMock()
        yaml_config.source.fields = [
            {"name": "field1", "type": "string"},
            {"name": "field2", "type": "int"},
            {"name": "field3", "type": "float"},
        ]
        yaml_config.source.watermark_field = "updated_at"
        yaml_config.dq_rules = MagicMock()
        yaml_config.dq_rules.soft_fail_threshold = 0.05
        yaml_config.dq_rules.hard_fail_threshold = 0.20

        result = yaml_config_to_domain(yaml_config)

        assert result.fields == ["field1", "field2", "field3"]
        assert result.watermark_field == "updated_at"

    def test_dq_config_mapping(self) -> None:
        """Test DQ config mapping."""
        yaml_config = MagicMock()
        yaml_config.pipeline_name = "test"
        yaml_config.provider = "test"
        yaml_config.entity_type = "test"
        yaml_config.primary_keys = ["id"]
        yaml_config.silver_table = "silver"
        yaml_config.gold_table = None
        yaml_config.gold_filter_types = None
        yaml_config.batch_size = 100
        yaml_config.checkpoint_interval = 1000
        yaml_config.source = MagicMock()
        yaml_config.source.fields = []
        yaml_config.source.watermark_field = None
        yaml_config.dq_rules = MagicMock()
        yaml_config.dq_rules.soft_fail_threshold = 0.10
        yaml_config.dq_rules.hard_fail_threshold = 0.30

        result = yaml_config_to_domain(yaml_config)

        assert isinstance(result.dq, DomainDQConfig)
        assert result.dq.soft_fail_threshold == 0.10
        assert result.dq.hard_fail_threshold == 0.30


@pytest.mark.unit
class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_cached(self) -> None:
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        with patch.dict(os.environ, {"BIOETL_ENV": "staging"}):
            settings1 = get_settings()
            settings2 = get_settings()

            assert settings1 is settings2

        # Clean up
        get_settings.cache_clear()
