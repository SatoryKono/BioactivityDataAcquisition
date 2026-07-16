"""Unit tests for configuration mapping."""

from __future__ import annotations

import pytest

from bioetl.domain.config import FieldPolicyConfig, PipelineConfig
from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.filter import compute_extraction_params_sha256
from bioetl.infrastructure.config._base import yaml_config_to_domain
from bioetl.infrastructure.schemas.pipeline_config import DQYamlConfig as YamlDQConfig
from bioetl.infrastructure.schemas.pipeline_config import (
    FieldPolicyConfigSchema,
    MaintenanceConfig,
    PipelineYamlConfig,
    SinkLayerConfig,
)


pytestmark = pytest.mark.unit


def test_yaml_config_to_domain_mapping():
    """Test mapping from YAML schema to Domain config."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        business_primary_keys=["id"],
        silver_table="silver.test",
        dq_overrides=YamlDQConfig(),
        sink={"silver": SinkLayerConfig(mode="append", sort_by=["id"])},
    )

    domain_config = yaml_config_to_domain(yaml_config)

    assert isinstance(domain_config, PipelineConfig)
    assert domain_config.pipeline_name == "test_pipeline"
    assert domain_config.table.silver_write_mode is SilverWriteMode.APPEND
    # Table config verification
    assert domain_config.table.silver_write_mode is SilverWriteMode.APPEND
    assert domain_config.table.silver_table == "silver.test"
    assert domain_config.table.silver_idempotency_contract is None
    assert domain_config.table.gold_idempotency_contract is None


def test_yaml_config_to_domain_default_mode():
    """Test default write mode is merge."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        business_primary_keys=["id"],
        silver_table="silver.test",
        dq_overrides=YamlDQConfig(),
    )

    domain_config = yaml_config_to_domain(yaml_config)

    assert domain_config.table.silver_write_mode is SilverWriteMode.MERGE


def test_yaml_config_to_domain_maps_sink_idempotency_contracts() -> None:
    """Explicit sink idempotency contracts must be preserved in domain config."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        business_primary_keys=["id"],
        silver_table="silver.test",
        sink={
            "silver": SinkLayerConfig(
                mode="append",
                idempotency_contract="append_log",
                sort_by=["id"],
            ),
            "gold": SinkLayerConfig(
                mode="overwrite",
                idempotency_contract="overwrite_rebuild",
                sort_by=["id"],
            ),
        },
    )

    domain_config = yaml_config_to_domain(yaml_config)

    assert domain_config.table.silver_idempotency_contract == "append_log"
    assert domain_config.table.gold_idempotency_contract == "overwrite_rebuild"


def test_pipeline_yaml_config_rejects_semantic_silver_filters() -> None:
    """Unified schema should fail closed on semantic Silver filters."""
    with pytest.raises(Exception, match=r"silver_filters\.columns"):
        PipelineYamlConfig.model_validate(
            {
                "pipeline_name": "test_pipeline",
                "provider": "test",
                "entity_type": "entity",
                "business_primary_keys": ["id"],
                "silver_table": "silver.test",
                "silver_filters": {
                    "required_fields": ["id"],
                    "columns": {"status": ["active"]},
                },
                "gold_filters": {
                    "columns": {"tier": ["gold"]},
                },
            }
        )


def test_yaml_config_to_domain_maps_source_profile() -> None:
    """Source-profile metadata must be part of resolved domain config."""
    extraction_params = {"standard_type__in": "IC50,Ki"}
    yaml_config = PipelineYamlConfig.model_validate(
        {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "business_primary_keys": ["id"],
            "silver_table": "silver.test",
            "extraction_params": extraction_params,
            "source_profile": {
                "profile_id": "test.entity.curated",
                "version": "1.0.0",
                "status": "baseline",
                "extraction_params_sha256": compute_extraction_params_sha256(
                    extraction_params
                ),
            },
        }
    )

    domain_config = yaml_config_to_domain(yaml_config)

    assert domain_config.source_profile is not None
    assert domain_config.source_profile.profile_id == "test.entity.curated"
    assert domain_config.source_profile.version == "1.0.0"


def test_pipeline_yaml_config_accepts_field_policy() -> None:
    """field_policy key must parse explicit field-level overrides."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        business_primary_keys=["id"],
        silver_table="silver.test",
        field_policy={
            "curation_flag": FieldPolicyConfigSchema(optional=False),
            "notes": FieldPolicyConfigSchema(optional=True),
        },
    )

    assert yaml_config.field_policy["curation_flag"].optional is False
    assert yaml_config.field_policy["notes"].optional is True


def test_pipeline_yaml_config_accepts_extended_field_policy() -> None:
    """Extended field_policy settings must parse from YAML."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        business_primary_keys=["id"],
        silver_table="silver.test",
        field_policy={
            "reviewed": FieldPolicyConfigSchema(
                optional=False,
                empty_as_missing=True,
                coercion_policy="no_string_coercion",
                boolean_true_values=["Yes", "ДА"],
                boolean_false_values=["No", "НЕТ"],
            ),
        },
    )

    reviewed = yaml_config.field_policy["reviewed"]

    assert reviewed.optional is False
    assert reviewed.empty_as_missing is True
    assert reviewed.coercion_policy == "no_string_coercion"
    assert reviewed.boolean_true_values == ["Yes", "ДА"]
    assert reviewed.boolean_false_values == ["No", "НЕТ"]


def test_pipeline_yaml_config_rejects_overlapping_boolean_vocabularies() -> None:
    """Overlapping boolean vocabularies must be rejected after normalization."""
    with pytest.raises(ValueError, match="must not overlap"):
        PipelineYamlConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            business_primary_keys=["id"],
            silver_table="silver.test",
            field_policy={
                "reviewed": FieldPolicyConfigSchema(
                    boolean_true_values=["Yes"],
                    boolean_false_values=[" yes "],
                ),
            },
        )


def test_yaml_config_to_domain_maps_field_policy() -> None:
    """Explicit field_policy overrides must be preserved in domain config."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        business_primary_keys=["id"],
        silver_table="silver.test",
        field_policy={
            "curation_flag": FieldPolicyConfigSchema(optional=False),
            "notes": FieldPolicyConfigSchema(optional=True),
        },
    )

    domain_config = yaml_config_to_domain(yaml_config)

    assert tuple(
        (policy.field, policy.optional) for policy in domain_config.field_policy
    ) == (
        ("curation_flag", False),
        ("notes", True),
    )


def test_yaml_config_to_domain_maps_extended_field_policy() -> None:
    """Extended field_policy values must be normalized into domain config."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        business_primary_keys=["id"],
        silver_table="silver.test",
        field_policy={
            "reviewed": FieldPolicyConfigSchema(
                optional=False,
                empty_as_missing=True,
                coercion_policy="no_string_coercion",
                boolean_true_values=["Yes", "ДА", " yes "],
                boolean_false_values=["No", "НЕТ"],
            ),
        },
    )

    domain_config = yaml_config_to_domain(yaml_config)

    assert domain_config.field_policy == (
        FieldPolicyConfig(
            field="reviewed",
            optional=False,
            empty_as_missing=True,
            coercion_policy="no_string_coercion",
            boolean_true_values=("yes", "да"),
            boolean_false_values=("no", "нет"),
        ),
    )


def test_pipeline_yaml_config_accepts_dq_overrides_key() -> None:
    """dq_overrides key must parse inline DQ config."""
    base = {
        "pipeline_name": "test_pipeline",
        "provider": "test",
        "entity_type": "entity",
        "business_primary_keys": ["id"],
        "silver_table": "silver.test",
    }

    cfg = PipelineYamlConfig.model_validate(
        {
            **base,
            "dq_overrides": {
                "soft_fail_threshold": 0.06,
                "hard_fail_threshold": 0.19,
            },
        }
    )

    assert cfg.dq_overrides.soft_fail_threshold == pytest.approx(0.06)
    assert cfg.dq_overrides.hard_fail_threshold == pytest.approx(0.19)


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
            business_primary_keys=["id"],
            silver_table="silver.test",
        )

        assert yaml_config.maintenance is not None
        assert yaml_config.maintenance.auto_vacuum is False
        assert yaml_config.maintenance.vacuum_retention_days == 7

    def test_pipeline_yaml_config_rejects_legacy_primary_keys_alias(self):
        """Legacy pipeline-YAML alias `primary_keys` is no longer accepted."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PipelineYamlConfig(
                pipeline_name="test_pipeline",
                provider="test",
                entity_type="entity",
                business_primary_keys=["id"],
                primary_keys=["id"],
                silver_table="silver.test",
            )

    def test_pipeline_yaml_config_rejects_legacy_schema_file_alias(self):
        """Legacy schema-file references are no longer accepted in pipeline YAML."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PipelineYamlConfig(
                pipeline_name="test_pipeline",
                provider="test",
                entity_type="entity",
                business_primary_keys=["id"],
                schema_file="../../schemas/test/entity.yaml",
                silver_table="silver.test",
            )

    def test_pipeline_yaml_config_maintenance_from_yaml(self):
        """Test PipelineYamlConfig parses maintenance from YAML dict."""
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "business_primary_keys": ["id"],
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
            "business_primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "silver": {"format": "parquet", "sort_by": ["id"]},
            },
        }

        with pytest.raises(ValueError, match="Silver layer MUST use 'delta' format"):
            PipelineYamlConfig.model_validate(config_dict)

    def test_gold_parquet_format_rejected(self):
        """Test that Parquet format is rejected for Gold layer (RULES.md §2.1)."""
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "business_primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "gold": {"format": "parquet", "sort_by": ["id"]},
            },
        }

        # Gold MUST use delta (RULES.md §2.1)
        with pytest.raises(ValueError, match="Gold layer MUST use 'delta' format"):
            PipelineYamlConfig.model_validate(config_dict)

    def test_silver_delta_format_accepted(self):
        """Test that Delta format is accepted for Silver layer."""
        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "business_primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "silver": {"format": "delta", "sort_by": ["id"]},
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
            "business_primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "gold": {"format": "delta", "sort_by": ["id"]},
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
            "business_primary_keys": ["id"],
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
            "business_primary_keys": ["id"],
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
            "business_primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "bronze": {"format": "parquet"},
            },
        }

        # Bronze format is auto-corrected to jsonl (RULES.md §2.1)
        yaml_config = PipelineYamlConfig.model_validate(config_dict)
        assert yaml_config.sink["bronze"].format == "jsonl"

    def test_silver_jsonl_format_rejected(self):
        """Test that JSONL format is rejected for Silver layer.

        Strict positive check: only 'delta' is allowed for Silver (RULES.md §2.1).
        Previously only 'parquet' was blocked, allowing 'jsonl' bypass.
        """
        from pydantic import ValidationError

        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "business_primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "silver": {"format": "jsonl", "sort_by": ["id"]},
            },
        }

        with pytest.raises(ValidationError, match="Silver layer MUST use 'delta'"):
            PipelineYamlConfig.model_validate(config_dict)

    def test_silver_csv_format_rejected(self):
        """Test that CSV format is rejected for Silver layer.

        CSV is not in the allowed literal types for SinkLayerConfig.format,
        so Pydantic rejects it at the type level before the validator runs.
        """
        from pydantic import ValidationError

        config_dict = {
            "pipeline_name": "test_pipeline",
            "provider": "test",
            "entity_type": "entity",
            "business_primary_keys": ["id"],
            "silver_table": "silver.test",
            "sink": {
                "silver": {"format": "csv"},
            },
        }

        with pytest.raises(ValidationError):
            PipelineYamlConfig.model_validate(config_dict)


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
            business_primary_keys=["id"],
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
            "business_primary_keys": ["id"],
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
            business_primary_keys=["id"],
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
            business_primary_keys=["id"],
            silver_table="silver.test",
        )

        domain_config = yaml_config_to_domain(yaml_config)

        assert domain_config.transform_version is None
        assert domain_config.transform_steps == ()
