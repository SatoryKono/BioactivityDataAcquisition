"""Unit tests for config mapper functions."""

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.mappers.config_mapper import (
    get_pipeline_config,
    yaml_config_to_domain,
)
from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config import PipelineConfig


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

    @patch("bioetl.composition.mappers.config_mapper.load_pipeline_config")
    def test_get_pipeline_config_cached(self, mock_load) -> None:
        """Test that get_pipeline_config is cached."""
        # Clean cache
        get_pipeline_config.cache_clear()

        # Mock load_pipeline_config
        mock_load.return_value = MagicMock(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
            gold_table=None,
            gold_filter_types=None,
            batch_size=100,
            checkpoint_interval=1000,
            source=MagicMock(fields=[], watermark_field=None),
            dq_rules=MagicMock(soft_fail_threshold=0.1, hard_fail_threshold=0.2),
        )

        res1 = get_pipeline_config("test")
        res2 = get_pipeline_config("test")

        assert res1 is res2
        mock_load.assert_called_once()
