"""Unit tests for FilterConfigLoader.

Tests hierarchical filter config loading and merge logic.

Requirements:
- REQ-CONF-010: Hierarchical filter config loading
- REQ-CONF-011: Filter config merge order (defaults -> provider -> entity)
- REQ-CONF-012: Inline override support for filters
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader


@pytest.fixture
def test_configs_root(tmp_path: Path) -> Path:
    """Create test config structure with hierarchical filter configs."""
    filter_root = tmp_path / "filter"
    filter_root.mkdir()

    # _defaults.yaml
    (filter_root / "_defaults.yaml").write_text(
        """
version: "1.0.0"

input_filter:
  enabled: false
  batch_size: 100

gold_filters:
  required_fields: []
  columns: {}
  ranges: {}
  list_lengths: {}
  list_contains: {}
  exclude_if_present: []
"""
    )

    # providers/test_provider.yaml
    providers = filter_root / "providers"
    providers.mkdir()
    (providers / "test_provider.yaml").write_text(
        """
version: "1.0.0"
provider: test_provider

input_filter:
  batch_size: 50

gold_filters:
  columns:
    provider_column: ["value1", "value2"]
"""
    )

    # entities/test_provider/test_entity.yaml
    entities = filter_root / "entities" / "test_provider"
    entities.mkdir(parents=True)
    (entities / "test_entity.yaml").write_text(
        """
version: "1.0.0"
provider: test_provider
entity: test_entity

input_filter:
  enabled: true
  source_path: "data/input/test.csv"
  column_name: "test_id"
  filter_field: "id"
  batch_size: 20

gold_filters:
  required_fields:
    - field_a
    - field_b
  columns:
    entity_column: ["v1", "v2", "v3"]
  ranges:
    value_field:
      min: 0
      max: 100
      include_min: true
      include_max: false
"""
    )

    return tmp_path


@pytest.fixture
def loader(test_configs_root: Path) -> FilterConfigLoader:
    """Create loader with test configs."""
    return FilterConfigLoader(test_configs_root)


class TestFilterConfigLoaderBasics:
    """Basic loading tests for FilterConfigLoader."""

    def test_load_defaults_only(self, loader: FilterConfigLoader) -> None:
        """Load for unknown provider should use defaults."""
        input_filter, gold_filters = loader.load("unknown_provider", "unknown_entity")

        assert input_filter.enabled is False
        assert input_filter.batch_size == 100
        assert len(gold_filters.required_fields) == 0
        assert len(gold_filters.column_filters) == 0

    def test_load_with_provider(self, loader: FilterConfigLoader) -> None:
        """Load with provider should merge provider config."""
        input_filter, gold_filters = loader.load("test_provider", "unknown_entity")

        # batch_size from provider
        assert input_filter.batch_size == 50
        # provider_column from provider
        assert len(gold_filters.column_filters) == 1
        assert gold_filters.column_filters[0].column == "provider_column"

    def test_load_full_hierarchy(self, loader: FilterConfigLoader) -> None:
        """Load with entity should merge all levels."""
        input_filter, gold_filters = loader.load("test_provider", "test_entity")

        # Input filter from entity
        assert input_filter.enabled is True
        assert input_filter.source_path == "data/input/test.csv"
        assert input_filter.column_name == "test_id"
        assert input_filter.filter_field == "id"
        assert input_filter.batch_size == 20

        # Gold filters from entity
        assert len(gold_filters.required_fields) == 2
        assert "field_a" in gold_filters.required_fields
        assert "field_b" in gold_filters.required_fields

        # Columns from provider + entity
        assert len(gold_filters.column_filters) == 2

        # Range filter from entity
        assert len(gold_filters.range_filters) == 1
        assert gold_filters.range_filters[0].column == "value_field"


class TestFilterConfigLoaderMerge:
    """Tests for merge behavior in FilterConfigLoader."""

    def test_batch_size_override(self, loader: FilterConfigLoader) -> None:
        """Entity batch_size should override provider."""
        input_filter, _ = loader.load("test_provider", "test_entity")

        assert input_filter.batch_size == 20  # from entity, not 50 from provider

    def test_columns_merge(self, loader: FilterConfigLoader) -> None:
        """Column filters should merge from all levels."""
        _, gold_filters = loader.load("test_provider", "test_entity")

        columns = {cf.column for cf in gold_filters.column_filters}
        assert "provider_column" in columns  # from provider
        assert "entity_column" in columns  # from entity

    def test_required_fields_concatenate(self, loader: FilterConfigLoader) -> None:
        """Required fields should concatenate from all levels."""
        _, gold_filters = loader.load("test_provider", "test_entity")

        assert "field_a" in gold_filters.required_fields
        assert "field_b" in gold_filters.required_fields


class TestFilterConfigLoaderInlineOverrides:
    """Tests for inline override handling."""

    def test_inline_override_batch_size(self, loader: FilterConfigLoader) -> None:
        """Inline overrides should be applied last."""
        input_filter, _ = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={"input_filter": {"batch_size": 200}},
        )

        assert input_filter.batch_size == 200

    def test_inline_override_enabled(self, loader: FilterConfigLoader) -> None:
        """Inline override for enabled."""
        input_filter, _ = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={"input_filter": {"enabled": False}},
        )

        assert input_filter.enabled is False

    def test_inline_override_gold_filters(self, loader: FilterConfigLoader) -> None:
        """Inline override for gold_filters."""
        _, gold_filters = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={
                "gold_filters": {
                    "required_fields": ["inline_field"],
                    "columns": {"inline_column": ["v1"]},
                }
            },
        )

        assert "inline_field" in gold_filters.required_fields
        columns = {cf.column for cf in gold_filters.column_filters}
        assert "inline_column" in columns


class TestFilterConfigLoaderCaching:
    """Tests for caching behavior."""

    def test_caching_same_config(self, loader: FilterConfigLoader) -> None:
        """Same config should be cached."""
        config1 = loader.load("test_provider", "test_entity")
        config2 = loader.load("test_provider", "test_entity")

        assert config1 is config2  # Same tuple from cache

    def test_no_cache_with_overrides(self, loader: FilterConfigLoader) -> None:
        """Configs with overrides should not be cached."""
        config1 = loader.load("test_provider", "test_entity")
        config2 = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={"input_filter": {"batch_size": 500}},
        )

        assert config1 is not config2

    def test_clear_cache(self, loader: FilterConfigLoader) -> None:
        """clear_cache() should invalidate cache."""
        config1 = loader.load("test_provider", "test_entity")
        loader.clear_cache()
        config2 = loader.load("test_provider", "test_entity")

        assert config1 is not config2

    def test_different_providers_different_cache(
        self, loader: FilterConfigLoader
    ) -> None:
        """Different providers should have separate cache entries."""
        config1 = loader.load("test_provider", "test_entity")
        config2 = loader.load("other_provider", "test_entity")

        assert config1 is not config2


class TestFilterConfigLoaderErrors:
    """Tests for error handling in FilterConfigLoader."""

    def test_missing_defaults_raises(self, tmp_path: Path) -> None:
        """Missing _defaults.yaml should raise FileNotFoundError."""
        filter_root = tmp_path / "filter"
        filter_root.mkdir()
        # No _defaults.yaml created

        loader = FilterConfigLoader(tmp_path)

        with pytest.raises(FileNotFoundError, match=r"_defaults\.yaml"):
            loader.load("any_provider", "any_entity")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML should raise appropriate error."""
        filter_root = tmp_path / "filter"
        filter_root.mkdir()
        (filter_root / "_defaults.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  batch_size: "not_a_number"
"""
        )

        loader = FilterConfigLoader(tmp_path)

        with pytest.raises(Exception):  # Pydantic ValidationError
            loader.load("any", "any")


class TestFilterDeepMerge:
    """Tests for _deep_merge logic specific to filter configs."""

    def test_scalar_override(self, loader: FilterConfigLoader) -> None:
        """Scalars should be overridden."""
        base = {"input_filter": {"batch_size": 100}}
        override = {"input_filter": {"batch_size": 50}}

        result = loader._deep_merge(base, override)

        assert result["input_filter"]["batch_size"] == 50

    def test_nested_dict_merge(self, loader: FilterConfigLoader) -> None:
        """Nested dicts should be merged recursively."""
        base = {"gold_filters": {"columns": {"col1": ["a"]}}}
        override = {"gold_filters": {"columns": {"col2": ["b"]}}}

        result = loader._deep_merge(base, override)

        assert result["gold_filters"]["columns"]["col1"] == ["a"]  # preserved
        assert result["gold_filters"]["columns"]["col2"] == ["b"]  # added

    def test_required_fields_concatenate(self, loader: FilterConfigLoader) -> None:
        """required_fields should concatenate with deduplication."""
        base = {"gold_filters": {"required_fields": ["field_a", "field_b"]}}
        override = {"gold_filters": {"required_fields": ["field_b", "field_c"]}}

        result = loader._deep_merge(base, override)

        fields = result["gold_filters"]["required_fields"]
        assert len(fields) == 3  # Deduplicated
        assert "field_a" in fields
        assert "field_b" in fields
        assert "field_c" in fields

    def test_exclude_if_present_concatenate(self, loader: FilterConfigLoader) -> None:
        """exclude_if_present should concatenate with deduplication."""
        base = {"gold_filters": {"exclude_if_present": ["field_x"]}}
        override = {"gold_filters": {"exclude_if_present": ["field_x", "field_y"]}}

        result = loader._deep_merge(base, override)

        fields = result["gold_filters"]["exclude_if_present"]
        assert len(fields) == 2  # Deduplicated
        assert "field_x" in fields
        assert "field_y" in fields

    def test_regular_list_override(self, loader: FilterConfigLoader) -> None:
        """Regular lists (not required_fields/exclude_if_present) should override."""
        base = {"gold_filters": {"columns": {"col": ["a", "b"]}}}
        override = {"gold_filters": {"columns": {"col": ["c", "d"]}}}

        result = loader._deep_merge(base, override)

        # List is completely overridden
        assert result["gold_filters"]["columns"]["col"] == ["c", "d"]

    def test_original_unchanged(self, loader: FilterConfigLoader) -> None:
        """Original dicts should not be modified."""
        base = {"input_filter": {"batch_size": 100}}
        override = {"input_filter": {"batch_size": 50}}

        loader._deep_merge(base, override)

        assert base["input_filter"]["batch_size"] == 100


class TestMergeStringLists:
    """Tests for _merge_string_lists logic."""

    def test_deduplicate(self, loader: FilterConfigLoader) -> None:
        """Lists should be deduplicated."""
        base = ["a", "b", "c"]
        override = ["b", "c", "d"]

        result = loader._merge_string_lists(base, override)

        assert result == ["a", "b", "c", "d"]

    def test_preserve_order(self, loader: FilterConfigLoader) -> None:
        """Order should be preserved (base items first)."""
        base = ["x", "y"]
        override = ["z"]

        result = loader._merge_string_lists(base, override)

        assert result == ["x", "y", "z"]

    def test_empty_base(self, loader: FilterConfigLoader) -> None:
        """Empty base should return override items."""
        base: list[str] = []
        override = ["a", "b"]

        result = loader._merge_string_lists(base, override)

        assert result == ["a", "b"]

    def test_empty_override(self, loader: FilterConfigLoader) -> None:
        """Empty override should return base items."""
        base = ["a", "b"]
        override: list[str] = []

        result = loader._merge_string_lists(base, override)

        assert result == ["a", "b"]


class TestFilterConfigFile:
    """Tests for FilterConfigFile Pydantic schema."""

    def test_to_domain_input_filter(self, loader: FilterConfigLoader) -> None:
        """Input filter should be converted correctly."""
        input_filter, _ = loader.load("test_provider", "test_entity")

        assert input_filter.enabled is True
        assert input_filter.source_path == "data/input/test.csv"
        assert input_filter.column_name == "test_id"
        assert input_filter.filter_field == "id"
        assert input_filter.batch_size == 20

    def test_to_domain_gold_filters(self, loader: FilterConfigLoader) -> None:
        """Gold filters should be converted correctly."""
        _, gold_filters = loader.load("test_provider", "test_entity")

        # Check required_fields
        assert "field_a" in gold_filters.required_fields
        assert "field_b" in gold_filters.required_fields

        # Check range filter
        range_filter = gold_filters.range_filters[0]
        assert range_filter.column == "value_field"
        assert range_filter.min_value == 0
        assert range_filter.max_value == 100
        assert range_filter.include_min is True
        assert range_filter.include_max is False


class TestFilterConfigLoaderIntegration:
    """Integration tests with actual filter config structure."""

    def test_load_with_list_filters(self, tmp_path: Path) -> None:
        """Test loading configs with list_lengths and list_contains."""
        filter_root = tmp_path / "filter"
        filter_root.mkdir()

        (filter_root / "_defaults.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  enabled: false
  batch_size: 100
gold_filters:
  required_fields: []
"""
        )

        entities = filter_root / "entities" / "test" / "test"
        entities.mkdir(parents=True)
        (entities.parent / "entity.yaml").write_text(
            """
version: "1.0.0"
gold_filters:
  list_lengths:
    components:
      min: 1
      max: 5
  list_contains:
    types:
      values: ["A", "B"]
      mode: any
"""
        )

        loader = FilterConfigLoader(tmp_path)
        _, gold_filters = loader.load("test", "entity")

        # Check list_length filter
        assert len(gold_filters.list_length_filters) == 1
        length_filter = gold_filters.list_length_filters[0]
        assert length_filter.column == "components"
        assert length_filter.min_length == 1
        assert length_filter.max_length == 5

        # Check list_contains filter
        assert len(gold_filters.list_contains_filters) == 1
        contains_filter = gold_filters.list_contains_filters[0]
        assert contains_filter.column == "types"
        assert contains_filter.values == frozenset(["A", "B"])
        assert contains_filter.mode == "any"
