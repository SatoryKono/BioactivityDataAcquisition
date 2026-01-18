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


@pytest.mark.unit
class TestMedallionFormatValidation:
    """Tests for Medallion Architecture format constraints (RULES.md §2.1)."""

    def test_silver_parquet_format_rejected(self):
        """Test that Parquet format is rejected for Silver layer."""
        from pydantic import ValidationError

        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "silver": {"format": "parquet"},
            },
        }

        with pytest.raises(ValidationError, match="Silver layer MUST use 'delta'"):
            PipelineYamlConfig.model_validate(config_dict)

    def test_gold_parquet_format_allowed(self):
        """Test that Parquet format is allowed for Gold layer (RULES.md §2.1)."""
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "gold": {"format": "parquet"},
            },
        }

        # Gold MAY use parquet (RULES.md §2.1)
        yaml_config = PipelineYamlConfig.model_validate(config_dict)
        assert yaml_config.sink["gold"].format == "parquet"

    def test_silver_delta_format_accepted(self):
        """Test that Delta format is accepted for Silver layer."""
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "silver": {"format": "delta"},
            },
        }

        yaml_config = PipelineYamlConfig.model_validate(config_dict)
        assert yaml_config.sink["silver"].format == "delta"

    def test_gold_delta_format_accepted(self):
        """Test that Delta format is accepted for Gold layer."""
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "gold": {"format": "delta"},
            },
        }

        yaml_config = PipelineYamlConfig.model_validate(config_dict)
        assert yaml_config.sink["gold"].format == "delta"

    def test_bronze_jsonl_format_accepted(self):
        """Test that JSONL format is accepted for Bronze layer."""
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "bronze": {"format": "jsonl"},
            },
        }

        yaml_config = PipelineYamlConfig.model_validate(config_dict)
        assert yaml_config.sink["bronze"].format == "jsonl"

    def test_bronze_delta_format_autocorrected_to_jsonl(self):
        """Test that Delta format is auto-corrected to JSONL for Bronze layer.

        RULES.md §2.1: Bronze MUST use JSONL format.
        The validator auto-corrects any format to jsonl.
        """
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "bronze": {"format": "delta"},
            },
        }

        # Bronze format is auto-corrected to jsonl (RULES.md §2.1)
        yaml_config = PipelineYamlConfig.model_validate(config_dict)
        assert yaml_config.sink["bronze"].format == "jsonl"

    def test_bronze_parquet_format_autocorrected_to_jsonl(self):
        """Test that Parquet format is auto-corrected to JSONL for Bronze layer.

        RULES.md §2.1: Bronze MUST use JSONL format.
        The validator auto-corrects any format to jsonl.
        """
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "bronze": {"format": "parquet"},
            },
        }

        # Bronze format is auto-corrected to jsonl (RULES.md §2.1)
        yaml_config = PipelineYamlConfig.model_validate(config_dict)
        assert yaml_config.sink["bronze"].format == "jsonl"


@pytest.mark.unit
class TestTransformConfig:
    """Tests for TransformConfig schema validation (lineage tracking)."""

    def test_transform_config_defaults(self):
        """Test TransformConfig has correct defaults (None/empty)."""
        from bioetl.infrastructure.schemas.pipeline_config import TransformConfig

        config = TransformConfig()

        assert config.version is None
        assert config.steps == []

    def test_transform_config_with_version_and_steps(self):
        """Test TransformConfig accepts version and steps."""
        from bioetl.infrastructure.schemas.pipeline_config import TransformConfig

        config = TransformConfig(
            version="1.0.0",
            steps=["normalize_values", "add_metadata", "calculate_hash"],
        )

        assert config.version == "1.0.0"
        assert config.steps == ["normalize_values", "add_metadata", "calculate_hash"]

    def test_transform_config_semver_validation_valid(self):
        """Test valid semver versions are accepted."""
        from bioetl.infrastructure.schemas.pipeline_config import TransformConfig

        valid_versions = [
            "1.0.0",
            "v1.0.0",
            "2.1.3",
            "0.0.1",
            "10.20.30",
            "1.0.0-alpha",
            "1.0.0-beta.1",
            "1.0.0+build.123",
            "1.2.3-alpha.1+build.456",
        ]

        for version in valid_versions:
            config = TransformConfig(version=version)
            assert config.version == version

    def test_transform_config_semver_validation_invalid(self):
        """Test invalid semver versions are rejected."""
        from pydantic import ValidationError

        from bioetl.infrastructure.schemas.pipeline_config import TransformConfig

        invalid_versions = [
            "1.0",  # Missing patch
            "1",  # Missing minor and patch
            "a.b.c",  # Non-numeric
            "1.0.0.0",  # Too many segments
            "1.0.0-",  # Incomplete pre-release
        ]

        for version in invalid_versions:
            with pytest.raises(ValidationError, match="Invalid semver format"):
                TransformConfig(version=version)

    def test_pipeline_yaml_config_has_transform_field(self):
        """Test PipelineYamlConfig includes transform field with defaults."""
        yaml_config = PipelineYamlConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            primary_keys=["id"],
            silver_table="silver.test",
        )

        assert yaml_config.transform is not None
        assert yaml_config.transform.version is None
        assert yaml_config.transform.steps == []

    def test_pipeline_yaml_config_transform_from_yaml(self):
        """Test PipelineYamlConfig parses transform from YAML dict."""
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "primary_keys": ["id"],
            "silver_table": "silver.test",
            "transform": {
                "version": "1.0.0",
                "steps": ["step1", "step2"],
            },
        }

        yaml_config = PipelineYamlConfig.model_validate(config_dict)

        assert yaml_config.transform.version == "1.0.0"
        assert yaml_config.transform.steps == ["step1", "step2"]

    def test_yaml_config_to_domain_includes_transform(self):
        """Test that yaml_config_to_domain extracts transform info."""
        from bioetl.infrastructure.schemas.pipeline_config import TransformConfig

        yaml_config = PipelineYamlConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            primary_keys=["id"],
            silver_table="silver.test",
            transform=TransformConfig(
                version="2.0.0",
                steps=["normalize", "validate", "hash"],
            ),
        )

        domain_config = yaml_config_to_domain(yaml_config)

        assert domain_config.transform_version == "2.0.0"
        assert domain_config.transform_steps == ("normalize", "validate", "hash")

    def test_yaml_config_to_domain_handles_empty_transform(self):
        """Test yaml_config_to_domain handles empty transform config."""
        yaml_config = PipelineYamlConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            primary_keys=["id"],
            silver_table="silver.test",
        )

        domain_config = yaml_config_to_domain(yaml_config)

        assert domain_config.transform_version is None
        assert domain_config.transform_steps == ()
