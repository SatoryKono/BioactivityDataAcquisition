"""Unit tests for domain configuration objects."""

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

        assert config.primary_keys == ["entity_id"]
        assert config.silver_table is None
        assert config.gold_table is None

    def test_custom_primary_keys(self) -> None:
        """Test custom primary keys."""
        config = TableConfig(primary_keys=["id", "version"])

        assert config.primary_keys == ["id", "version"]

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

    def test_not_hashable_due_to_list(self) -> None:
        """Test that TableConfig is not hashable due to list field."""
        config = TableConfig(silver_table="test")

        # Lists are not hashable, so frozen dataclass with list field isn't hashable
        with pytest.raises(TypeError, match="unhashable"):
            hash(config)

    def test_empty_primary_keys(self) -> None:
        """Test with empty primary keys list."""
        config = TableConfig(primary_keys=[])

        assert config.primary_keys == []

    def test_multiple_primary_keys(self) -> None:
        """Test with multiple primary keys."""
        keys = ["org_id", "entity_id", "version"]
        config = TableConfig(primary_keys=keys)

        assert config.primary_keys == keys
        assert len(config.primary_keys) == 3

    def test_full_configuration(self) -> None:
        """Test with all fields specified."""
        config = TableConfig(
            primary_keys=["activity_id", "assay_chembl_id"],
            silver_table="chembl_activity_silver",
            gold_table="chembl_activity_gold",
        )

        assert config.primary_keys == ["activity_id", "assay_chembl_id"]
        assert config.silver_table == "chembl_activity_silver"
        assert config.gold_table == "chembl_activity_gold"
