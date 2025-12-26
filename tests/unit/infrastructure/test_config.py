"""Unit tests for configuration mapping."""

from __future__ import annotations

import pytest

from bioetl.domain.config import PipelineConfig
from bioetl.infrastructure.config import yaml_config_to_domain
from bioetl.infrastructure.schemas.pipeline_config import DQConfig as YamlDQConfig
from bioetl.infrastructure.schemas.pipeline_config import (
    MaintenanceConfig,
    PipelineYamlConfig,
    SinkLayerConfig,
)


def test_yaml_config_to_domain_mapping():
    """Test mapping from YAML schema to Domain config."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        primary_keys=["id"],
        silver_table="silver.test",
        dq_rules=YamlDQConfig(),
        sink={"silver": SinkLayerConfig(mode="append")},
    )

    domain_config = yaml_config_to_domain(yaml_config)

    assert isinstance(domain_config, PipelineConfig)
    assert domain_config.pipeline_name == "test_pipeline"
    assert domain_config.write_mode == "append"
    # Table config verification
    assert domain_config.table.silver_write_mode == "append"
    assert domain_config.table.silver_table == "silver.test"


def test_yaml_config_to_domain_default_mode():
    """Test default write mode is merge."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        primary_keys=["id"],
        silver_table="silver.test",
        dq_rules=YamlDQConfig(),
    )

    domain_config = yaml_config_to_domain(yaml_config)

    assert domain_config.write_mode == "merge"


@pytest.mark.unit
class TestMaintenanceConfig:
    """Tests for MaintenanceConfig schema validation."""

    def test_maintenance_config_defaults(self):
        """Test MaintenanceConfig has correct defaults."""
        config = MaintenanceConfig()

        assert config.auto_vacuum is False
        assert config.vacuum_retention_days == 7

    def test_maintenance_config_custom_values(self):
        """Test MaintenanceConfig accepts custom values."""
        config = MaintenanceConfig(
            auto_vacuum=True,
            vacuum_retention_days=30,
        )

        assert config.auto_vacuum is True
        assert config.vacuum_retention_days == 30

    def test_maintenance_config_validation_min_retention_days(self):
        """Test vacuum_retention_days cannot be less than 1."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MaintenanceConfig(vacuum_retention_days=0)

    def test_maintenance_config_validation_max_retention_days(self):
        """Test vacuum_retention_days cannot exceed 365."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MaintenanceConfig(vacuum_retention_days=400)

    def test_pipeline_yaml_config_has_maintenance_field(self):
        """Test PipelineYamlConfig includes maintenance field with defaults."""
        yaml_config = PipelineYamlConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            primary_keys=["id"],
            silver_table="silver.test",
        )

        assert yaml_config.maintenance is not None
        assert yaml_config.maintenance.auto_vacuum is False
        assert yaml_config.maintenance.vacuum_retention_days == 7

    def test_pipeline_yaml_config_maintenance_from_yaml(self):
        """Test PipelineYamlConfig parses maintenance from YAML dict."""
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "primary_keys": ["id"],
            "silver_table": "silver.test",
            "maintenance": {
                "auto_vacuum": True,
                "vacuum_retention_days": 14,
            },
        }

        yaml_config = PipelineYamlConfig.model_validate(config_dict)

        assert yaml_config.maintenance.auto_vacuum is True
        assert yaml_config.maintenance.vacuum_retention_days == 14
