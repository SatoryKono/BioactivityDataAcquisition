"""Unit tests for infrastructure config settings classes."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config import PipelineConfig
from bioetl.composition.mappers.config_mapper import yaml_config_to_domain
from bioetl.infrastructure.config import (
    PipelineSettings,
    Settings,
    get_settings,
)


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

        assert isinstance(settings.pipeline, PipelineSettings)

    def test_data_dir_default(self, monkeypatch) -> None:
        """Test data_dir default value."""
        monkeypatch.delenv("BIOETL_ENV", raising=False)
        settings = Settings(test_mode=True, _env_file=None)
        assert settings.data_dir == Path("data")

    def test_data_dir_custom(self, monkeypatch) -> None:
        """Test custom data_dir."""
        monkeypatch.delenv("BIOETL_ENV", raising=False)
        settings = Settings(test_mode=True, data_dir=Path("/custom/data"), _env_file=None)
        assert settings.data_dir == Path("/custom/data")

    def test_path_properties(self, monkeypatch) -> None:
        """Test bronze_path, silver_path, gold_path, checkpoint_path properties."""
        monkeypatch.delenv("BIOETL_ENV", raising=False)
        settings = Settings(test_mode=True, data_dir=Path("/data"), _env_file=None)

        assert settings.bronze_path == Path("/data/bronze")
        assert settings.silver_path == Path("/data/silver")
        assert settings.gold_path == Path("/data/gold")
        assert settings.checkpoint_path == Path("/data/checkpoints")

    def test_staging_env(self, monkeypatch) -> None:
        """Test that staging env works."""
        monkeypatch.setenv("BIOETL_ENV", "staging")
        get_settings.cache_clear()
        settings = Settings()
        assert settings.env == "staging"

    def test_prod_env(self, monkeypatch) -> None:
        """Test that prod env works."""
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
        yaml_config.gold_filters = MagicMock()
        yaml_config.gold_filters.columns = {}
        yaml_config.gold_filters.required_fields = []
        yaml_config.gold_filters.exclude_if_present = []
        yaml_config.batch_size = 200
        yaml_config.checkpoint_interval = 2000
        yaml_config.source = MagicMock()
        yaml_config.source.fields = []
        yaml_config.dq_rules = MagicMock()
        yaml_config.dq_rules.soft_fail_threshold = 0.05
        yaml_config.dq_rules.hard_fail_threshold = 0.20

        result = yaml_config_to_domain(yaml_config)

        assert isinstance(result, PipelineConfig)
        assert result.pipeline_name == "test_pipeline"
        assert result.provider == "test"
        assert result.entity_type == "entity"
        assert result.primary_keys == ("id",)  # Lists converted to tuples
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
        yaml_config.gold_filters = MagicMock()
        yaml_config.gold_filters.columns = {}
        yaml_config.gold_filters.required_fields = []
        yaml_config.gold_filters.exclude_if_present = []
        yaml_config.batch_size = 100
        yaml_config.checkpoint_interval = 1000
        yaml_config.source = MagicMock()
        yaml_config.source.fields = [
            {"name": "field1", "type": "string"},
            {"name": "field2", "type": "int"},
            {"name": "field3", "type": "float"},
        ]
        yaml_config.dq_rules = MagicMock()
        yaml_config.dq_rules.soft_fail_threshold = 0.05
        yaml_config.dq_rules.hard_fail_threshold = 0.20

        result = yaml_config_to_domain(yaml_config)

        assert result.fields == ("field1", "field2", "field3")

    def test_dq_config_mapping(self) -> None:
        """Test DQ config mapping."""
        yaml_config = MagicMock()
        yaml_config.pipeline_name = "test"
        yaml_config.provider = "test"
        yaml_config.entity_type = "test"
        yaml_config.primary_keys = ["id"]
        yaml_config.silver_table = "silver"
        yaml_config.gold_table = None
        yaml_config.gold_filters = MagicMock()
        yaml_config.gold_filters.columns = {}
        yaml_config.gold_filters.required_fields = []
        yaml_config.gold_filters.exclude_if_present = []
        yaml_config.batch_size = 100
        yaml_config.checkpoint_interval = 1000
        yaml_config.source = MagicMock()
        yaml_config.source.fields = []
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
