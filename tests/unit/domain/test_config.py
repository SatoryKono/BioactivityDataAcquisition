"""Unit tests for domain configuration objects."""

from __future__ import annotations

import pytest

from bioetl.domain.config import (
    DEFAULT_VALIDATION_CONFIG,
    DQConfig,
    TableConfig,
    ValidationConfig,
)


@pytest.mark.unit
class TestDQConfig:
    """Tests for DQConfig dataclass."""

    def test_dq_config_default_threshold_values(self) -> None:
        """Test default threshold values."""
        config = DQConfig()

        assert config.soft_fail_threshold == pytest.approx(0.05)
        assert config.hard_fail_threshold == pytest.approx(0.50)

    def test_dq_config_accepts_custom_threshold_values(self) -> None:
        """Test custom threshold values."""
        config = DQConfig(soft_fail_threshold=0.10, hard_fail_threshold=0.30)

        assert config.soft_fail_threshold == pytest.approx(0.10)
        assert config.hard_fail_threshold == pytest.approx(0.30)

    def test_dq_config_is_immutable(self) -> None:
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

        assert config.soft_fail_threshold == pytest.approx(0.0)
        assert config.hard_fail_threshold == pytest.approx(0.01)

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

    def test_table_config_default_values(self) -> None:
        """Test default configuration values."""
        config = TableConfig()

        assert config.primary_keys == ("entity_id",)
        assert config.silver_table is None
        assert config.gold_table is None

    def test_custom_primary_keys__test_table_config_unit_domain_test_config_88(
        self,
    ) -> None:
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

    def test_table_config_is_immutable(self) -> None:
        """Test that TableConfig is frozen (immutable)."""
        config = TableConfig()

        with pytest.raises(AttributeError):
            config.silver_table = "new_table"  # type: ignore[misc]

    def test_config_table_config__equality__7a7a757c(self) -> None:
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
            primary_keys=["activity_id", "assay_id"],
            silver_table="chembl_activity_silver",
            gold_table="chembl_activity_gold",
        )

        assert config.primary_keys == ("activity_id", "assay_id")
        assert config.silver_table == "chembl_activity_silver"
        assert config.gold_table == "chembl_activity_gold"


@pytest.mark.unit
class TestValidationConfig:
    """Tests for ValidationConfig dataclass."""

    def test_validation_config_default_range_values(self) -> None:
        """Test default validation range values."""
        config = ValidationConfig()

        assert config.min_publication_year == 1500
        assert config.max_publication_year == 2100
        assert config.min_molecular_weight == pytest.approx(10.0)
        assert config.max_molecular_weight == pytest.approx(10_000.0)
        assert config.molecular_weight_precision == 10
        assert config.max_pmid == 10_000_000_000
        assert config.max_taxonomy_id == 10_000_000
        assert config.min_pchembl_value == pytest.approx(0.0)
        assert config.max_pchembl_value == pytest.approx(15.0)

    def test_custom_publication_year_range(self) -> None:
        """Test custom publication year range (e.g., for Semantic Scholar)."""
        config = ValidationConfig(min_publication_year=1500, max_publication_year=2100)

        assert config.min_publication_year == 1500
        assert config.max_publication_year == 2100

    def test_custom_molecular_weight_range(self) -> None:
        """Test custom molecular weight range."""
        config = ValidationConfig(
            min_molecular_weight=1.0, max_molecular_weight=50_000.0
        )

        assert config.min_molecular_weight == pytest.approx(1.0)
        assert config.max_molecular_weight == pytest.approx(50_000.0)

    def test_validation_config_is_immutable(self) -> None:
        """Test that ValidationConfig is frozen (immutable)."""
        config = ValidationConfig()

        with pytest.raises(AttributeError):
            config.min_publication_year = 1500  # type: ignore[misc]

    def test_validation_config__equality__0aaa2e94(self) -> None:
        """Test equality between ValidationConfig instances."""
        config1 = ValidationConfig()
        config2 = ValidationConfig()
        config3 = ValidationConfig(min_publication_year=1600)

        assert config1 == config2
        assert config1 != config3

    def test_validation_config__hashable__cb205035(self) -> None:
        """Test that ValidationConfig is hashable."""
        config1 = ValidationConfig()
        config2 = ValidationConfig()

        config_set = {config1, config2}
        assert len(config_set) == 1

    def test_invalid_year_range_raises(self) -> None:
        """Test that invalid year range (min >= max) raises ValueError."""
        with pytest.raises(ValueError, match="min_publication_year"):
            ValidationConfig(min_publication_year=2100, max_publication_year=1500)

    def test_invalid_year_range_equal_raises(self) -> None:
        """Test that equal year range raises ValueError."""
        with pytest.raises(ValueError, match="min_publication_year"):
            ValidationConfig(min_publication_year=2000, max_publication_year=2000)

    def test_invalid_mw_range_raises(self) -> None:
        """Test that invalid MW range (min >= max) raises ValueError."""
        with pytest.raises(ValueError, match="min_molecular_weight"):
            ValidationConfig(min_molecular_weight=10000.0, max_molecular_weight=10.0)

    def test_invalid_pchembl_range_raises(self) -> None:
        """Test that invalid pChEMBL range raises ValueError."""
        with pytest.raises(ValueError, match="min_pchembl_value"):
            ValidationConfig(min_pchembl_value=15.0, max_pchembl_value=0.0)

    def test_negative_precision_raises(self) -> None:
        """Test that negative precision raises ValueError."""
        with pytest.raises(ValueError, match="molecular_weight_precision"):
            ValidationConfig(molecular_weight_precision=-1)

    def test_zero_precision_valid(self) -> None:
        """Test that zero precision is valid (rounds to integers)."""
        config = ValidationConfig(molecular_weight_precision=0)
        assert config.molecular_weight_precision == 0

    def test_default_singleton_available(self) -> None:
        """Test that DEFAULT_VALIDATION_CONFIG singleton is available."""
        assert DEFAULT_VALIDATION_CONFIG is not None
        assert isinstance(DEFAULT_VALIDATION_CONFIG, ValidationConfig)
        assert DEFAULT_VALIDATION_CONFIG.min_publication_year == 1500

    def test_semantic_scholar_config(self) -> None:
        """Test Semantic Scholar-specific config with min_year=1500."""
        ss_config = ValidationConfig(min_publication_year=1500)

        assert ss_config.min_publication_year == 1500
        # Other values remain at defaults
        assert ss_config.max_publication_year == 2100
        assert ss_config.min_molecular_weight == pytest.approx(10.0)
