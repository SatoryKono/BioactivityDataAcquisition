"""Unit tests for domain configuration objects."""

from __future__ import annotations

import pytest

from bioetl.domain.config import DQConfig, TableConfig


@pytest.mark.unit
class TestDQConfig:
    """Tests for DQConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default threshold values."""
        config = DQConfig()

        assert config.soft_fail_threshold == 0.05
        assert config.hard_fail_threshold == 0.20

    def test_custom_values(self) -> None:
        """Test custom threshold values."""
        config = DQConfig(soft_fail_threshold=0.10, hard_fail_threshold=0.30)

        assert config.soft_fail_threshold == 0.10
        assert config.hard_fail_threshold == 0.30

    def test_immutability(self) -> None:
        """Test that DQConfig is frozen (immutable)."""
        config = DQConfig()

        with pytest.raises(AttributeError):
            config.soft_fail_threshold = 0.10  # type: ignore[misc]

    def test_equality(self) -> None:
        """Test equality between DQConfig instances."""
        config1 = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)
        config2 = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)
        config3 = DQConfig(soft_fail_threshold=0.10, hard_fail_threshold=0.20)

        assert config1 == config2
        assert config1 != config3

    def test_hashable(self) -> None:
        """Test that DQConfig is hashable (can be used in sets/dicts)."""
        config1 = DQConfig()
        config2 = DQConfig()

        config_set = {config1, config2}
        assert len(config_set) == 1  # Same values = same hash

    def test_zero_soft_threshold(self) -> None:
        """Test with zero soft threshold (hard must be greater)."""
        config = DQConfig(soft_fail_threshold=0.0, hard_fail_threshold=0.01)

        assert config.soft_fail_threshold == 0.0
        assert config.hard_fail_threshold == 0.01

    def test_invalid_equal_thresholds(self) -> None:
        """Test that equal thresholds raise ValueError."""
        with pytest.raises(ValueError, match="strictly less than"):
            DQConfig(soft_fail_threshold=0.1, hard_fail_threshold=0.1)

    def test_threshold_ordering(self) -> None:
        """Test that thresholds can be compared."""
        config = DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20)

        assert config.soft_fail_threshold < config.hard_fail_threshold


@pytest.mark.unit
class TestTableConfig:
    """Tests for TableConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = TableConfig()

        assert config.primary_keys == ("entity_id",)
        assert config.silver_table is None
        assert config.gold_table is None

    def test_custom_primary_keys(self) -> None:
        """Test custom primary keys."""
        config = TableConfig(primary_keys=["id", "version"])

        # Lists are converted to tuples
        assert config.primary_keys == ("id", "version")

    def test_custom_table_names(self) -> None:
        """Test custom table names."""
        config = TableConfig(
            silver_table="my_silver_table",
            gold_table="my_gold_table",
        )

        assert config.silver_table == "my_silver_table"
        assert config.gold_table == "my_gold_table"

    def test_immutability(self) -> None:
        """Test that TableConfig is frozen (immutable)."""
        config = TableConfig()

        with pytest.raises(AttributeError):
            config.silver_table = "new_table"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Test equality between TableConfig instances."""
        config1 = TableConfig(primary_keys=["id"], silver_table="silver")
        config2 = TableConfig(primary_keys=["id"], silver_table="silver")
        config3 = TableConfig(primary_keys=["id"], silver_table="other")

        assert config1 == config2
        assert config1 != config3

    def test_hashable_with_tuple(self) -> None:
        """Test that TableConfig is hashable with tuple fields."""
        config1 = TableConfig(silver_table="test")
        config2 = TableConfig(silver_table="test")

        # Tuples are hashable, so frozen dataclass with tuple field is hashable
        assert hash(config1) == hash(config2)

        # Can be used in sets/dicts
        config_set = {config1, config2}
        assert len(config_set) == 1

    def test_immutable_primary_keys(self) -> None:
        """Test that primary_keys tuple cannot be mutated."""
        config = TableConfig(primary_keys=["id", "version"])

        # Tuples don't support item assignment - raises TypeError
        with pytest.raises(TypeError):
            config.primary_keys[0] = "new_key"  # type: ignore[index]

    def test_immutable_partition_cols(self) -> None:
        """Test that partition_cols tuple cannot be mutated."""
        config = TableConfig(partition_cols=["col1", "col2"])

        # Tuples don't support item assignment - raises TypeError
        with pytest.raises(TypeError):
            config.partition_cols[0] = "col3"  # type: ignore[index]

    def test_list_to_tuple_conversion(self) -> None:
        """Test that incoming lists are converted to tuples."""
        config = TableConfig(
            primary_keys=["id", "version"],
            partition_cols=["col1"],
        )

        assert isinstance(config.primary_keys, tuple)
        assert isinstance(config.partition_cols, tuple)
        assert config.primary_keys == ("id", "version")
        assert config.partition_cols == ("col1",)

    def test_empty_primary_keys(self) -> None:
        """Test with empty primary keys."""
        config = TableConfig(primary_keys=[])

        assert config.primary_keys == ()

    def test_multiple_primary_keys(self) -> None:
        """Test with multiple primary keys."""
        keys = ["org_id", "entity_id", "version"]
        config = TableConfig(primary_keys=keys)

        assert config.primary_keys == ("org_id", "entity_id", "version")
        assert len(config.primary_keys) == 3

    def test_full_configuration(self) -> None:
        """Test with all fields specified."""
        config = TableConfig(
            primary_keys=["activity_id", "assay_chembl_id"],
            silver_table="chembl_activity_silver",
            gold_table="chembl_activity_gold",
        )

        assert config.primary_keys == ("activity_id", "assay_chembl_id")
        assert config.silver_table == "chembl_activity_silver"
        assert config.gold_table == "chembl_activity_gold"
