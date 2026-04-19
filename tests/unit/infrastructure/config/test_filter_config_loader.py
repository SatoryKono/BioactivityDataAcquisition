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

from bioetl.domain.filtering import SilverFilterConfig
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader


@pytest.fixture
def test_configs_root(tmp_path: Path) -> Path:
    """Create test config structure with hierarchical filter configs."""
    base_root = tmp_path / "base"
    base_root.mkdir(parents=True)
    (base_root / "pipeline.yaml").write_text(
        """
version: "1.0.0"

input_filter:
  enabled: false
  batch_size: 100

filter_defaults:
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
    providers = tmp_path / "providers"
    providers.mkdir()
    (providers / "test_provider.yaml").write_text(
        """
version: "1.0.0"
provider: test_provider

filters:
  input_filter:
    batch_size: 50
  gold_filters:
    columns:
      provider_column: ["value1", "value2"]
"""
    )

    # entities/test_provider/test_entity.yaml
    entities = tmp_path / "entities" / "test_provider"
    entities.mkdir(parents=True)
    (entities / "test_entity.yaml").write_text(
        """
version: "1.0.0"
provider: test_provider
entity: test_entity

filters:
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
        input_filter, _, gold_filters, _ = loader.load(
            "unknown_provider", "unknown_entity"
        )

        assert input_filter.enabled is False
        assert input_filter.batch_size == 100
        assert len(gold_filters.required_fields) == 0
        assert len(gold_filters.column_filters) == 0

    def test_load_with_provider(self, loader: FilterConfigLoader) -> None:
        """Load with provider should merge provider config."""
        input_filter, _, gold_filters, _ = loader.load(
            "test_provider", "unknown_entity"
        )

        # batch_size from provider
        assert input_filter.batch_size == 50
        # provider_column from provider
        assert len(gold_filters.column_filters) == 1
        assert gold_filters.column_filters[0].column == "provider_column"

    def test_load_full_hierarchy(self, loader: FilterConfigLoader) -> None:
        """Load with entity should merge all levels."""
        input_filter, _, gold_filters, _ = loader.load("test_provider", "test_entity")

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

    def test_load_defaults_from_base_pipeline(self, tmp_path: Path) -> None:
        """Loader should read defaults from configs/base/pipeline.yaml."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "pipeline.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  enabled: false
  batch_size: 333
filter_defaults:
  gold_filters:
    required_fields: [base_required]
    columns: {}
    ranges: {}
    list_lengths: {}
    list_contains: {}
    exclude_if_present: []
"""
        )

        loader = FilterConfigLoader(tmp_path)
        input_filter, _, gold_filters, _ = loader.load("missing_provider", "missing")

        assert input_filter.batch_size == 333
        assert "base_required" in gold_filters.required_fields

    def test_load_provider_layer_from_unified_provider_file(
        self, tmp_path: Path
    ) -> None:
        """Provider-level filters should load from configs/providers/{provider}.yaml."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "pipeline.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  enabled: false
  batch_size: 100
filter_defaults:
  gold_filters:
    required_fields: []
    columns: {}
    ranges: {}
    list_lengths: {}
    list_contains: {}
    exclude_if_present: []
"""
        )

        providers_root = tmp_path / "providers"
        providers_root.mkdir(parents=True)
        (providers_root / "test_provider.yaml").write_text(
            """
version: "1.0.0"
provider: test_provider
filters:
  input_filter:
    batch_size: 77
  gold_filters:
    columns:
      provider_column: ["from_provider"]
"""
        )

        loader = FilterConfigLoader(tmp_path)
        input_filter, _, gold_filters, _ = loader.load("test_provider", "missing")
        assert input_filter.batch_size == 77
        assert "provider_column" in {c.column for c in gold_filters.column_filters}

    def test_load_entity_layer_from_unified_entity_file(self, tmp_path: Path) -> None:
        """Entity-level filters should load from configs/entities/{p}/{e}.yaml."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "pipeline.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  enabled: false
  batch_size: 100
filter_defaults:
  gold_filters:
    required_fields: []
    columns: {}
    ranges: {}
    list_lengths: {}
    list_contains: {}
    exclude_if_present: []
"""
        )

        entities_root = tmp_path / "entities" / "test_provider"
        entities_root.mkdir(parents=True)
        (entities_root / "test_entity.yaml").write_text(
            """
version: "1.0.0"
provider: test_provider
entity: test_entity
filters:
  input_filter:
    batch_size: 44
  gold_filters:
    required_fields: [entity_field]
"""
        )

        loader = FilterConfigLoader(tmp_path)
        input_filter, _, gold_filters, _ = loader.load("test_provider", "test_entity")
        assert input_filter.batch_size == 44
        assert "entity_field" in gold_filters.required_fields


class TestFilterConfigLoaderMerge:
    """Tests for merge behavior in FilterConfigLoader."""

    def test_batch_size_override(self, loader: FilterConfigLoader) -> None:
        """Entity batch_size should override provider."""
        input_filter, _, _, _ = loader.load("test_provider", "test_entity")

        assert input_filter.batch_size == 20  # from entity, not 50 from provider

    def test_columns_merge(self, loader: FilterConfigLoader) -> None:
        """Column filters should merge from all levels."""
        _, _, gold_filters, _ = loader.load("test_provider", "test_entity")

        columns = {cf.column for cf in gold_filters.column_filters}
        assert "provider_column" in columns  # from provider
        assert "entity_column" in columns  # from entity

    def test_required_fields_concatenate(self, loader: FilterConfigLoader) -> None:
        """Required fields should concatenate from all levels."""
        _, _, gold_filters, _ = loader.load("test_provider", "test_entity")

        assert "field_a" in gold_filters.required_fields
        assert "field_b" in gold_filters.required_fields


class TestFilterConfigLoaderInlineOverrides:
    """Tests for inline override handling."""

    def test_inline_override_batch_size(self, loader: FilterConfigLoader) -> None:
        """Inline overrides should be applied last."""
        input_filter, _, _, _ = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={"input_filter": {"batch_size": 200}},
        )

        assert input_filter.batch_size == 200

    def test_inline_override_enabled(self, loader: FilterConfigLoader) -> None:
        """Inline override for enabled."""
        input_filter, _, _, _ = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={"input_filter": {"enabled": False}},
        )

        assert input_filter.enabled is False

    def test_inline_override_gold_filters(self, loader: FilterConfigLoader) -> None:
        """Inline override for gold_filters."""
        _, _, gold_filters, _ = loader.load(
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

        assert config1 == config2
        assert len(loader._cache) == 1

    def test_no_cache_with_overrides(self, loader: FilterConfigLoader) -> None:
        """Configs with overrides should not be cached."""
        config1 = loader.load("test_provider", "test_entity")
        config2 = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={"input_filter": {"batch_size": 500}},
        )

        assert config1 != config2
        assert len(loader._cache) == 1

    def test_clear_cache(self, loader: FilterConfigLoader) -> None:
        """clear_cache() should invalidate cache."""
        config1 = loader.load("test_provider", "test_entity")
        loader.clear_cache()
        config2 = loader.load("test_provider", "test_entity")

        assert config1 == config2
        assert len(loader._cache) == 1

    def test_different_providers_different_cache(
        self, loader: FilterConfigLoader
    ) -> None:
        """Different providers should have separate cache entries."""
        config1 = loader.load("test_provider", "test_entity")
        config2 = loader.load("other_provider", "test_entity")

        assert config1 != config2
        assert len(loader._cache) == 2


class TestFilterConfigLoaderErrors:
    """Tests for error handling in FilterConfigLoader."""

    def test_missing_defaults_raises(self, tmp_path: Path) -> None:
        """Missing filter_defaults in base pipeline should raise FileNotFoundError."""
        loader = FilterConfigLoader(tmp_path)

        with pytest.raises(FileNotFoundError, match="filter_defaults"):
            loader.load("any_provider", "any_entity")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML should raise appropriate error."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "pipeline.yaml").write_text(
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
        input_filter, _, _, _ = loader.load("test_provider", "test_entity")

        assert input_filter.enabled is True
        assert input_filter.source_path == "data/input/test.csv"
        assert input_filter.column_name == "test_id"
        assert input_filter.filter_field == "id"
        assert input_filter.batch_size == 20

    def test_to_domain_silver_filters_type(self, loader: FilterConfigLoader) -> None:
        """Silver filters should be converted to SilverFilterConfig."""
        _, silver_filters, _, _ = loader.load("test_provider", "test_entity")

        assert isinstance(silver_filters, SilverFilterConfig)

    def test_to_domain_gold_filters(self, loader: FilterConfigLoader) -> None:
        """Gold filters should be converted correctly."""
        _, _, gold_filters, _ = loader.load("test_provider", "test_entity")

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


class TestFilterConfigLoaderExtractionParams:
    """Tests for extraction_params loading via FilterConfigLoader."""

    def test_extraction_params_default_empty(self, loader: FilterConfigLoader) -> None:
        """Extraction params should be empty when not configured."""
        _, _, _, extraction_params = loader.load("test_provider", "test_entity")
        assert extraction_params.is_empty

    def test_extraction_params_from_entity_config(self, tmp_path: Path) -> None:
        """Extraction params should be loaded from entity config."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "pipeline.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  enabled: false
  batch_size: 100
filter_defaults:
  gold_filters:
    required_fields: []
"""
        )

        entities = tmp_path / "entities" / "chembl"
        entities.mkdir(parents=True)
        (entities / "activity.yaml").write_text(
            """
version: "1.0.0"
provider: chembl
entity: activity
extraction_params:
  standard_type__in: "IC50,Ki"
  standard_units: "nM"
  potential_duplicate: 0
  data_validity_comment__isnull: true
"""
        )

        loader = FilterConfigLoader(tmp_path)
        _, _, _, extraction_params = loader.load("chembl", "activity")

        assert not extraction_params.is_empty
        assert extraction_params.params["standard_type__in"] == "IC50,Ki"
        assert extraction_params.params["standard_units"] == "nM"
        assert extraction_params.params["potential_duplicate"] == 0
        assert extraction_params.params["data_validity_comment__isnull"] is True

    def test_extraction_params_inline_override(self, tmp_path: Path) -> None:
        """Inline overrides should update extraction_params."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "pipeline.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  enabled: false
filter_defaults:
  gold_filters:
    required_fields: []
  extraction_params:
    standard_type__in: "IC50"
"""
        )

        loader = FilterConfigLoader(tmp_path)
        _, _, _, extraction_params = loader.load(
            "any",
            "any",
            inline_overrides={"extraction_params": {"standard_type__in": "Ki"}},
        )

        assert extraction_params.params["standard_type__in"] == "Ki"


class TestAssayExtractionParamsLoading:
    """Tests for assay extraction_params loading via FilterConfigLoader."""

    def test_assay_extraction_params_loaded(self, tmp_path: Path) -> None:
        """Extraction params should be loaded from assay entity config."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "pipeline.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  enabled: false
  batch_size: 100
filter_defaults:
  gold_filters:
    required_fields: []
"""
        )

        entities = tmp_path / "entities" / "chembl"
        entities.mkdir(parents=True)
        (entities / "assay.yaml").write_text(
            """
version: "1.0.0"
provider: chembl
entity: assay
input_filter:
  enabled: true
  source_path: "data/input/assay.csv"
  column_name: "assay_chembl_id"
  filter_field: "assay_id"
  batch_size: 20
extraction_params:
  assay_type__in: "B,F"
  confidence_score__gte: 8
  relationship_type: "D"
  target_chembl_id__isnull: false
silver_filters:
  columns:
    assay_type: [B, F]
    relationship_type: [D]
  ranges:
    confidence_score:
      min: 8
      max: 9
  required_fields:
    - assay_id
    - assay_type
    - description
    - target_chembl_id
gold_filters:
  columns:
    assay_type: [B, F]
    confidence_score: ["8", "9"]
    relationship_type: [D]
  required_fields:
    - assay_type
    - description
"""
        )

        loader = FilterConfigLoader(tmp_path)
        input_filter, _, _, extraction_params = loader.load(
            "chembl", "assay"
        )

        # Extraction params loaded
        assert not extraction_params.is_empty
        assert extraction_params.params["assay_type__in"] == "B,F"
        assert extraction_params.params["confidence_score__gte"] == 8
        assert extraction_params.params["relationship_type"] == "D"
        assert extraction_params.params["target_chembl_id__isnull"] is False

        # Input filter still enabled alongside extraction_params
        assert input_filter.enabled is True
        assert input_filter.filter_field == "assay_id"

    def test_assay_extraction_params_no_input_filter_overlap(
        self, tmp_path: Path
    ) -> None:
        """Assay extraction_params keys should not overlap with input_filter field."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "pipeline.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  enabled: false
filter_defaults:
  gold_filters:
    required_fields: []
"""
        )

        entities = tmp_path / "entities" / "chembl"
        entities.mkdir(parents=True)
        (entities / "assay.yaml").write_text(
            """
version: "1.0.0"
provider: chembl
entity: assay
input_filter:
  enabled: true
  source_path: "data/input/assay.csv"
  column_name: "assay_chembl_id"
  filter_field: "assay_id"
  batch_size: 20
extraction_params:
  assay_type__in: "B,F"
  confidence_score__gte: 8
  relationship_type: "D"
  target_chembl_id__isnull: false
gold_filters:
  required_fields: []
"""
        )

        loader = FilterConfigLoader(tmp_path)
        input_filter, _, _, extraction_params = loader.load("chembl", "assay")

        # No overlap: input_filter uses "assay_id", extraction_params has other keys
        assert input_filter.filter_field not in extraction_params.params

    def test_assay_silver_filters_loaded(self, tmp_path: Path) -> None:
        """Silver filters should be loaded from assay entity config."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "pipeline.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  enabled: false
filter_defaults:
  gold_filters:
    required_fields: []
"""
        )

        entities = tmp_path / "entities" / "chembl"
        entities.mkdir(parents=True)
        (entities / "assay.yaml").write_text(
            """
version: "1.0.0"
provider: chembl
entity: assay
silver_filters:
  columns:
    assay_type: [B, F]
    relationship_type: [D]
  ranges:
    confidence_score:
      min: 8
      max: 9
  required_fields:
    - assay_id
    - assay_type
    - description
    - target_chembl_id
gold_filters:
  required_fields: []
"""
        )

        loader = FilterConfigLoader(tmp_path)
        _, silver_filters, _, _ = loader.load("chembl", "assay")

        assert isinstance(silver_filters, SilverFilterConfig)
        # Column filters
        columns = {cf.column for cf in silver_filters.column_filters}
        assert "assay_type" in columns
        assert "relationship_type" in columns
        # Range filter
        assert len(silver_filters.range_filters) == 1
        assert silver_filters.range_filters[0].column == "confidence_score"
        assert silver_filters.range_filters[0].min_value == 8
        assert silver_filters.range_filters[0].max_value == 9
        # Required fields
        assert "assay_id" in silver_filters.required_fields
        assert "target_chembl_id" in silver_filters.required_fields


class TestFilterConfigLoaderIntegration:
    """Integration tests with actual filter config structure."""

    def test_load_with_list_filters(self, tmp_path: Path) -> None:
        """Test loading configs with list_lengths and list_contains."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "pipeline.yaml").write_text(
            """
version: "1.0.0"
input_filter:
  enabled: false
  batch_size: 100
filter_defaults:
  gold_filters:
    required_fields: []
"""
        )

        entities = tmp_path / "entities" / "test"
        entities.mkdir(parents=True)
        (entities / "entity.yaml").write_text(
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
        _, _, gold_filters, _ = loader.load("test", "entity")

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


def test_filter_loader_reads_base_pipeline_defaults(tmp_path: Path) -> None:
    """Loader should read defaults from configs/base/pipeline.yaml."""
    base_root = tmp_path / "base"
    base_root.mkdir(parents=True)
    (base_root / "pipeline.yaml").write_text(
        """
version: "1.0.0"
input_filter:
  enabled: false
  batch_size: 111
filter_defaults:
  gold_filters:
    required_fields: []
"""
    )

    loader = FilterConfigLoader(tmp_path)
    input_filter, _, _, _ = loader.load("missing", "missing")
    assert input_filter.batch_size == 111
