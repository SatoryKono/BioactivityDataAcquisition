"""Unit tests for infrastructure config settings classes."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config import PipelineConfig
from bioetl.infrastructure.config import (
    PipelineSettings,
    Settings,
    get_settings,
    yaml_config_to_domain,
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
        assert settings.heartbeat_interval == 30

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
        with pytest.raises(ValidationError):
            PipelineSettings(batch_size=0)

        with pytest.raises(ValidationError):
            PipelineSettings(batch_size=10001)

    def test_heartbeat_interval_validation(self) -> None:
        """Test heartbeat_interval validation."""
        # Valid boundaries
        settings = PipelineSettings(heartbeat_interval=5)
        assert settings.heartbeat_interval == 5

        settings = PipelineSettings(heartbeat_interval=60)
        assert settings.heartbeat_interval == 60

        # Invalid
        with pytest.raises(ValidationError):
            PipelineSettings(heartbeat_interval=4)

        with pytest.raises(ValidationError):
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
        settings = Settings(
            test_mode=True, data_dir=Path("/custom/data"), _env_file=None
        )
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
        """Test basic config mapping with real Pydantic models."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            DQConfig,
            GoldFiltersConfig,
            PipelineYamlConfig,
            SourceConfig,
        )

        yaml_config = PipelineYamlConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            primary_keys=["id"],
            silver_table="silver_table",
            gold_table="gold_table",
            gold_filters=GoldFiltersConfig(),
            batch_size=200,
            checkpoint_interval=2000,
            source=SourceConfig(),
            dq_rules=DQConfig(
                soft_fail_threshold=0.05,
                hard_fail_threshold=0.20,
            ),
            sink={},
        )

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
        from bioetl.infrastructure.schemas.pipeline_config import (
            DQConfig,
            GoldFiltersConfig,
            PipelineYamlConfig,
            SourceConfig,
        )

        yaml_config = PipelineYamlConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
            gold_table=None,
            gold_filters=GoldFiltersConfig(),
            batch_size=100,
            checkpoint_interval=1000,
            source=SourceConfig(
                fields=[
                    {"name": "field1", "type": "string"},
                    {"name": "field2", "type": "int"},
                    {"name": "field3", "type": "float"},
                ]
            ),
            dq_rules=DQConfig(
                soft_fail_threshold=0.05,
                hard_fail_threshold=0.20,
            ),
            sink={},
        )

        result = yaml_config_to_domain(yaml_config)

        assert result.fields == ("field1", "field2", "field3")

    def test_dq_config_mapping(self) -> None:
        """Test DQ config mapping with real Pydantic models."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            DQConfig,
            GoldFiltersConfig,
            PipelineYamlConfig,
            SourceConfig,
        )

        yaml_config = PipelineYamlConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
            gold_table=None,
            gold_filters=GoldFiltersConfig(),
            batch_size=100,
            checkpoint_interval=1000,
            source=SourceConfig(),
            dq_rules=DQConfig(
                soft_fail_threshold=0.10,
                hard_fail_threshold=0.30,
            ),
            sink={},
        )

        result = yaml_config_to_domain(yaml_config)

        assert isinstance(result.dq, DomainDQConfig)
        assert result.dq.soft_fail_threshold == 0.10
        assert result.dq.hard_fail_threshold == 0.30

    def test_pipeline_yaml_config_to_domain_method(self) -> None:
        """Test PipelineYamlConfig.to_domain() method provides consistent API."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            DQConfig,
            GoldFiltersConfig,
            PipelineYamlConfig,
            SourceConfig,
        )

        yaml_config = PipelineYamlConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
            gold_table=None,
            gold_filters=GoldFiltersConfig(),
            batch_size=100,
            checkpoint_interval=1000,
            source=SourceConfig(),
            dq_rules=DQConfig(),
            sink={},
        )

        # Test that to_domain() method works and is equivalent to yaml_config_to_domain()
        result_method = yaml_config.to_domain()
        result_function = yaml_config_to_domain(yaml_config)

        assert isinstance(result_method, PipelineConfig)
        assert result_method.pipeline_name == result_function.pipeline_name
        assert result_method.provider == result_function.provider
        assert (
            result_method.dq.soft_fail_threshold
            == result_function.dq.soft_fail_threshold
        )

    def test_gold_filters_config_to_domain_method(self) -> None:
        """Test GoldFiltersConfig.to_domain() method."""
        from bioetl.domain.filtering import GoldFilterConfig
        from bioetl.infrastructure.schemas.pipeline_config import (
            GoldFiltersConfig,
            GoldListContainsFilterConfig,
            GoldListLengthFilterConfig,
            GoldRangeFilterConfig,
        )

        gold_filters = GoldFiltersConfig(
            columns={"status": ["active", "approved"]},
            ranges={"score": GoldRangeFilterConfig(min=0.5, max=1.0)},
            list_lengths={"targets": GoldListLengthFilterConfig(min=1, max=10)},
            list_contains={"tags": GoldListContainsFilterConfig(values=["important"])},
            required_fields=["name", "id"],
            exclude_if_present=["deprecated"],
        )

        result = gold_filters.to_domain()

        assert isinstance(result, GoldFilterConfig)
        assert len(result.column_filters) == 1
        assert len(result.range_filters) == 1
        assert len(result.list_length_filters) == 1
        assert len(result.list_contains_filters) == 1
        assert result.required_fields == ("name", "id")
        assert result.exclude_if_present == ("deprecated",)


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
