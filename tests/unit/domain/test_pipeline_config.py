"""Unit tests for domain PipelineConfig."""

from __future__ import annotations

import pytest

from bioetl.domain.config import DQConfig, PipelineConfig


@pytest.mark.unit
class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_minimal_valid_config(self) -> None:
        """Test creation with minimal required fields."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="test_provider",
            entity_type="test_entity",
            primary_keys=["id"],
            silver_table="test_silver",
        )

        assert config.pipeline_name == "test_pipeline"
        assert config.provider == "test_provider"
        assert config.entity_type == "test_entity"
        assert config.primary_keys == ("id",)  # Lists converted to tuples
        assert config.silver_table == "test_silver"

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
        )

        assert config.gold_table is None
        assert config.batch_size == 100
        assert config.checkpoint_interval == 1000
        assert config.fields == ()  # Empty tuple
        assert isinstance(config.dq, DQConfig)

    def test_custom_batch_size(self) -> None:
        """Test custom batch size."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
            batch_size=500,
        )

        assert config.batch_size == 500

    def test_custom_checkpoint_interval(self) -> None:
        """Test custom checkpoint interval."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
            checkpoint_interval=5000,
        )

        assert config.checkpoint_interval == 5000

    def test_custom_dq_config(self) -> None:
        """Test custom DQ config."""
        dq = DQConfig(soft_fail_threshold=0.10, hard_fail_threshold=0.50)
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
            dq=dq,
        )

        assert config.dq.soft_fail_threshold == 0.10
        assert config.dq.hard_fail_threshold == 0.50

    def test_fields_tuple(self) -> None:
        """Test fields configuration (converted to tuple)."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
            fields=["field1", "field2", "field3"],
        )

        assert config.fields == ("field1", "field2", "field3")
        assert isinstance(config.fields, tuple)

    def test_lock_key_property(self) -> None:
        """Test lock_key property generation."""
        config = PipelineConfig(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="silver",
        )

        assert config.lock_key == "pipeline:chembl_activity"

    def test_immutability(self) -> None:
        """Test that PipelineConfig is frozen (immutable)."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
        )

        with pytest.raises(AttributeError):
            config.pipeline_name = "new_name"  # type: ignore[misc]

    # Validation tests

    def test_empty_pipeline_name_raises(self) -> None:
        """Test that empty pipeline_name raises ValueError."""
        with pytest.raises(ValueError, match="pipeline_name cannot be empty"):
            PipelineConfig(
                pipeline_name="",
                provider="test",
                entity_type="test",
                primary_keys=["id"],
                silver_table="silver",
            )

    def test_empty_provider_raises(self) -> None:
        """Test that empty provider raises ValueError."""
        with pytest.raises(ValueError, match="provider cannot be empty"):
            PipelineConfig(
                pipeline_name="test",
                provider="",
                entity_type="test",
                primary_keys=["id"],
                silver_table="silver",
            )

    def test_empty_entity_type_raises(self) -> None:
        """Test that empty entity_type raises ValueError."""
        with pytest.raises(ValueError, match="entity_type cannot be empty"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="",
                primary_keys=["id"],
                silver_table="silver",
            )

    def test_zero_batch_size_raises(self) -> None:
        """Test that zero batch_size raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                primary_keys=["id"],
                silver_table="silver",
                batch_size=0,
            )

    def test_negative_batch_size_raises(self) -> None:
        """Test that negative batch_size raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                primary_keys=["id"],
                silver_table="silver",
                batch_size=-10,
            )

    def test_zero_checkpoint_interval_raises(self) -> None:
        """Test that zero checkpoint_interval raises ValueError."""
        with pytest.raises(ValueError, match="checkpoint_interval must be positive"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                primary_keys=["id"],
                silver_table="silver",
                checkpoint_interval=0,
            )

    def test_negative_checkpoint_interval_raises(self) -> None:
        """Test that negative checkpoint_interval raises ValueError."""
        with pytest.raises(ValueError, match="checkpoint_interval must be positive"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                primary_keys=["id"],
                silver_table="silver",
                checkpoint_interval=-100,
            )

    def test_empty_primary_keys_raises(self) -> None:
        """Test that empty primary_keys raises ValueError."""
        with pytest.raises(ValueError, match="primary_keys cannot be empty"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                primary_keys=[],
                silver_table="silver",
            )

    def test_multiple_primary_keys(self) -> None:
        """Test configuration with multiple primary keys."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["org_id", "entity_id", "version"],
            silver_table="silver",
        )

        assert len(config.primary_keys) == 3
        assert "org_id" in config.primary_keys
        assert "entity_id" in config.primary_keys
        assert "version" in config.primary_keys

    def test_full_configuration(self) -> None:
        """Test with all fields specified."""
        dq = DQConfig(soft_fail_threshold=0.02, hard_fail_threshold=0.10)
        config = PipelineConfig(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id", "assay_chembl_id"],
            silver_table="chembl_activity_silver",
            gold_table="chembl_activity_gold",
            batch_size=250,
            checkpoint_interval=2500,
            fields=[
                "activity_id",
                "assay_chembl_id",
                "standard_value",
                "pchembl_value",
            ],
            dq=dq,
        )

        assert config.pipeline_name == "chembl_activity"
        assert config.provider == "chembl"
        assert config.entity_type == "activity"
        assert config.primary_keys == ("activity_id", "assay_chembl_id")
        assert config.silver_table == "chembl_activity_silver"
        assert config.gold_table == "chembl_activity_gold"
        assert config.batch_size == 250
        assert config.checkpoint_interval == 2500
        assert len(config.fields) == 4
        assert config.dq.soft_fail_threshold == 0.02
        assert config.lock_key == "pipeline:chembl_activity"

    def test_equality(self) -> None:
        """Test equality between PipelineConfig instances."""
        config1 = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
        )
        config2 = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
        )
        config3 = PipelineConfig(
            pipeline_name="other",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
        )

        assert config1 == config2
        assert config1 != config3

    def test_hashable_with_tuple(self) -> None:
        """Test that PipelineConfig is hashable with tuple fields."""
        config1 = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
        )
        config2 = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
        )

        # Tuples are hashable, so frozen dataclass with tuple field is hashable
        assert hash(config1) == hash(config2)

        # Can be used in sets/dicts
        config_set = {config1, config2}
        assert len(config_set) == 1

    def test_immutable_primary_keys(self) -> None:
        """Test that primary_keys tuple cannot be mutated."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id", "version"],
            silver_table="silver",
        )

        # Tuples don't support item assignment - raises TypeError
        with pytest.raises(TypeError):
            config.primary_keys[0] = "new_key"  # type: ignore[index]

    def test_immutable_fields(self) -> None:
        """Test that fields tuple cannot be mutated."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id"],
            silver_table="silver",
            fields=["field1", "field2"],
        )

        # Tuples don't support item assignment - raises TypeError
        with pytest.raises(TypeError):
            config.fields[0] = "field3"  # type: ignore[index]

    def test_list_to_tuple_conversion(self) -> None:
        """Test that incoming lists are converted to tuples."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            primary_keys=["id", "version"],
            silver_table="silver",
            partition_cols=["col1"],
            fields=["f1", "f2"],
        )

        assert isinstance(config.primary_keys, tuple)
        assert isinstance(config.partition_cols, tuple)
        assert isinstance(config.fields, tuple)
        assert config.primary_keys == ("id", "version")
        assert config.partition_cols == ("col1",)
        assert config.fields == ("f1", "f2")
