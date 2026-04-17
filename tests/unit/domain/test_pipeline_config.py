"""Unit tests for domain PipelineConfig."""

from __future__ import annotations

import pytest

from bioetl.domain.config import DQConfig, PipelineConfig, TableConfig
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode


def _make_config(**overrides: object) -> PipelineConfig:
    """Create a PipelineConfig with sensible defaults, allowing overrides."""
    defaults: dict[str, object] = {
        "pipeline_name": "test",
        "provider": "test",
        "entity_type": "test",
        "table": TableConfig(primary_keys=("id",), silver_table="silver"),
    }
    defaults.update(overrides)
    return PipelineConfig(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_minimal_valid_config(self) -> None:
        """Test creation with minimal required fields."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="test_provider",
            entity_type="test_entity",
            table=TableConfig(primary_keys=["id"], silver_table="test_silver"),
        )

        assert config.pipeline_name == "test_pipeline"
        assert config.provider == "test_provider"
        assert config.entity_type == "test_entity"
        assert config.table.primary_keys == ("id",)  # Lists converted to tuples
        assert config.effective_silver_table == "test_silver"

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        config = _make_config()

        assert config.effective_gold_table == f"{config.provider}.{config.entity_type}"
        assert config.batch_size == 100
        assert config.checkpoint_interval == 1000
        assert config.fields == ()  # Empty tuple
        assert isinstance(config.dq, DQConfig)

    def test_custom_batch_size(self) -> None:
        """Test custom batch size."""
        config = _make_config(batch_size=500)
        assert config.batch_size == 500

    def test_custom_checkpoint_interval(self) -> None:
        """Test custom checkpoint interval."""
        config = _make_config(checkpoint_interval=5000)
        assert config.checkpoint_interval == 5000

    def test_custom_dq_config(self) -> None:
        """Test custom DQ config."""
        dq = DQConfig(soft_fail_threshold=0.10, hard_fail_threshold=0.50)
        config = _make_config(dq=dq)

        assert config.dq.soft_fail_threshold == pytest.approx(0.10)
        assert config.dq.hard_fail_threshold == pytest.approx(0.50)

    def test_fields_tuple(self) -> None:
        """Test fields configuration (converted to tuple)."""
        config = _make_config(fields=["field1", "field2", "field3"])

        assert config.fields == ("field1", "field2", "field3")
        assert isinstance(config.fields, tuple)

    def test_lock_key_property(self) -> None:
        """Test lock_key property generation."""
        config = PipelineConfig(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            table=TableConfig(primary_keys=["activity_id"], silver_table="silver"),
        )

        assert config.lock_key == "pipeline:chembl_activity"

    def test_immutability(self) -> None:
        """Test that PipelineConfig is frozen (immutable)."""
        config = _make_config()

        with pytest.raises(AttributeError):
            config.pipeline_name = "new_name"  # type: ignore[misc]

    # Validation tests

    def test_empty_pipeline_name_raises(self) -> None:
        """Test that empty pipeline_name raises ValueError."""
        with pytest.raises(ValueError, match="pipeline_name cannot be empty"):
            _make_config(pipeline_name="")

    def test_empty_provider_raises(self) -> None:
        """Test that empty provider raises ValueError."""
        with pytest.raises(ValueError, match="provider cannot be empty"):
            _make_config(provider="")

    def test_empty_entity_type_raises(self) -> None:
        """Test that empty entity_type raises ValueError."""
        with pytest.raises(ValueError, match="entity_type cannot be empty"):
            _make_config(entity_type="")

    def test_zero_batch_size_raises(self) -> None:
        """Test that zero batch_size raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            _make_config(batch_size=0)

    def test_negative_batch_size_raises(self) -> None:
        """Test that negative batch_size raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            _make_config(batch_size=-10)

    def test_zero_checkpoint_interval_raises(self) -> None:
        """Test that zero checkpoint_interval raises ValueError."""
        with pytest.raises(ValueError, match="checkpoint_interval must be positive"):
            _make_config(checkpoint_interval=0)

    def test_negative_checkpoint_interval_raises(self) -> None:
        """Test that negative checkpoint_interval raises ValueError."""
        with pytest.raises(ValueError, match="checkpoint_interval must be positive"):
            _make_config(checkpoint_interval=-100)

    def test_empty_primary_keys_raises(self) -> None:
        """Test that empty primary_keys raises ValueError."""
        with pytest.raises(ValueError, match="primary_keys cannot be empty"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                table=TableConfig(primary_keys=[], silver_table="silver"),
            )

    def test_multiple_primary_keys(self) -> None:
        """Test configuration with multiple primary keys."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            table=TableConfig(
                primary_keys=["org_id", "entity_id", "version"],
                silver_table="silver",
            ),
        )

        assert len(config.table.primary_keys) == 3
        assert "org_id" in config.table.primary_keys
        assert "entity_id" in config.table.primary_keys
        assert "version" in config.table.primary_keys

    def test_full_configuration(self) -> None:
        """Test with all fields specified."""
        dq = DQConfig(soft_fail_threshold=0.02, hard_fail_threshold=0.10)
        config = PipelineConfig(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            table=TableConfig(
                primary_keys=["activity_id", "assay_id"],
                silver_table="chembl_activity_silver",
                gold_table="chembl_activity_gold",
            ),
            batch_size=250,
            checkpoint_interval=2500,
            fields=[
                "activity_id",
                "assay_id",
                "standard_value",
                "pchembl_value",
            ],
            dq=dq,
        )

        assert config.pipeline_name == "chembl_activity"
        assert config.provider == "chembl"
        assert config.entity_type == "activity"
        assert config.table.primary_keys == ("activity_id", "assay_id")
        assert config.effective_silver_table == "chembl_activity_silver"
        assert config.effective_gold_table == "chembl_activity_gold"
        assert config.batch_size == 250
        assert config.checkpoint_interval == 2500
        assert len(config.fields) == 4
        assert config.dq.soft_fail_threshold == pytest.approx(0.02)
        assert config.lock_key == "pipeline:chembl_activity"

    def test_equality(self) -> None:
        """Test equality between PipelineConfig instances."""
        table = TableConfig(primary_keys=["id"], silver_table="silver")
        config1 = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            table=table,
        )
        config2 = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            table=table,
        )
        config3 = PipelineConfig(
            pipeline_name="other",
            provider="test",
            entity_type="test",
            table=table,
        )

        assert config1 == config2
        assert config1 != config3

    def test_hashable_with_tuple(self) -> None:
        """Test that PipelineConfig is hashable with tuple fields."""
        table = TableConfig(primary_keys=["id"], silver_table="silver")
        config1 = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            table=table,
        )
        config2 = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            table=table,
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
            table=TableConfig(primary_keys=["id", "version"], silver_table="silver"),
        )

        # Tuples don't support item assignment - raises TypeError
        with pytest.raises(TypeError):
            config.table.primary_keys[0] = "new_key"  # type: ignore[index]

    def test_immutable_fields(self) -> None:
        """Test that fields tuple cannot be mutated."""
        config = _make_config(fields=["field1", "field2"])

        # Tuples don't support item assignment - raises TypeError
        with pytest.raises(TypeError):
            config.fields[0] = "field3"  # type: ignore[index]

    def test_immutable_transform_steps(self) -> None:
        """Test that transform_steps tuple cannot be mutated."""
        config = _make_config(transform_steps=["step1", "step2"])

        with pytest.raises(TypeError):
            config.transform_steps[0] = "new_step"  # type: ignore[index]

    def test_immutable_dq_config(self) -> None:
        """Test that dq config cannot be replaced or mutated."""
        config = _make_config(dq=DQConfig())

        # Cannot replace dq attribute
        with pytest.raises(AttributeError):
            config.dq = DQConfig()  # type: ignore[misc]

        # Cannot mutate dq object (it is frozen)
        with pytest.raises(AttributeError):
            config.dq.soft_fail_threshold = 0.5  # type: ignore[misc]

    def test_list_to_tuple_conversion(self) -> None:
        """Test that incoming lists are converted to tuples."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            table=TableConfig(
                primary_keys=["id", "version"],
                silver_table="silver",
                partition_cols=["col1"],
            ),
            fields=["f1", "f2"],
        )

        assert isinstance(config.table.primary_keys, tuple)
        assert isinstance(config.table.partition_cols, tuple)
        assert isinstance(config.fields, tuple)
        assert config.table.primary_keys == ("id", "version")
        assert config.table.partition_cols == ("col1",)
        assert config.fields == ("f1", "f2")

    def test_table_field_is_single_source_of_truth(self) -> None:
        """Test that table field provides table config directly."""
        table = TableConfig(
            primary_keys=["id"],
            silver_table="my_silver",
            gold_table="my_gold",
            silver_write_mode=SilverWriteMode.MERGE,
            gold_write_mode=GoldWriteMode.APPEND,
        )
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            table=table,
        )

        # Direct access via table field
        assert config.table is table
        assert config.table.silver_table == "my_silver"
        assert config.table.gold_table == "my_gold"

        # Convenience properties forward correctly
        assert config.effective_silver_table == config.table.silver_table
        assert config.effective_gold_table == config.table.gold_table
        assert config.table.primary_keys == ("id",)
        assert config.table.silver_write_mode == SilverWriteMode.MERGE
        assert config.table.gold_write_mode == GoldWriteMode.APPEND
        assert config.table.partition_cols == ()
        assert config.table.on_schema_mismatch == "error"
