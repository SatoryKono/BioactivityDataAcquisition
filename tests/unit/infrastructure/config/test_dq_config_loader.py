"""Unit tests for DQConfigLoader.

Tests hierarchical config loading and merge logic.

Requirements:
- REQ-CONF-001: Hierarchical DQ config loading
- REQ-CONF-002: Config merge order (defaults -> provider -> entity)
- REQ-CONF-003: Inline override support
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader


@pytest.fixture(scope="class")
def test_configs_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create test config structure with hierarchical DQ configs."""
    tmp_path = tmp_path_factory.mktemp("dq_configs")
    base_root = tmp_path / "base"
    base_root.mkdir()
    (base_root / "quality.yaml").write_text(
        """
version: "1.0.0"

thresholds:
  soft_fail: 0.05
  hard_fail: 0.20

strict_validation: false
invalid_record_policy: quarantine

report:
  enabled: true
  format: json
  sample_size: 10

common_field_validations:
  - field: _content_hash
    type: required
    nullable: false
    error_message: "Content hash required"

  - field: common_field
    type: pattern
    pattern: '^COMMON'
    nullable: true

common_cross_field_validations: []
"""
    )

    # providers/test_provider.yaml
    providers = tmp_path / "providers"
    providers.mkdir()
    (providers / "test_provider.yaml").write_text(
        """
version: "1.0.0"
provider: test_provider

quality:
  thresholds:
    soft_fail: 0.05
    hard_fail: 0.15
  provider_field_validations:
    - field: provider_field
      type: pattern
      pattern: '^TEST'
      nullable: true
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

quality:
  entity_field_validations:
    - field: entity_field
      type: range
      min: 0
      max: 100
      nullable: true
  entity_cross_field_validations:
    - name: test_cross
      fields:
        - field_a
        - field_b
      condition: all_present
  key_nullability:
    - field: entity_id
      key_type: merge
      nullable: false
"""
    )

    return tmp_path


@pytest.fixture
def loader(test_configs_root: Path) -> DQConfigLoader:
    """Create loader with test configs."""
    return DQConfigLoader(test_configs_root)


class TestDQConfigLoaderBasics:
    """Basic loading tests for DQConfigLoader."""

    def test_load_defaults_only(self, loader: DQConfigLoader) -> None:
        """Load for unknown provider should use defaults."""
        config = loader.load("unknown_provider", "unknown_entity")

        assert config.soft_fail_threshold == pytest.approx(0.05)
        assert config.hard_fail_threshold == pytest.approx(0.20)
        assert config.strict_validation is False
        # Only common validations (from base/quality.yaml)
        assert len(config.field_validations) == 2  # _content_hash + common_field

    def test_load_with_provider(self, loader: DQConfigLoader) -> None:
        """Load with provider should merge provider config."""
        config = loader.load("test_provider", "unknown_entity")

        assert config.soft_fail_threshold == pytest.approx(0.05)  # from defaults
        assert config.hard_fail_threshold == pytest.approx(
            0.15
        )  # from provider (override)
        # common (2) + provider (1)
        assert len(config.field_validations) == 3

    def test_load_full_hierarchy(self, loader: DQConfigLoader) -> None:
        """Load with entity should merge all levels."""
        config = loader.load("test_provider", "test_entity")

        assert config.soft_fail_threshold == pytest.approx(0.05)  # from defaults
        assert config.hard_fail_threshold == pytest.approx(0.15)  # from provider
        # common (2) + provider (1) + entity (1)
        assert len(config.field_validations) == 4
        # Cross-field from entity
        assert len(config.cross_field_validations) == 1
        assert len(config.key_nullability_rules) == 1
        assert config.key_nullability_rules[0].field == "entity_id"

    def test_load_defaults_from_base_quality(self, tmp_path: Path) -> None:
        """Loader should read defaults from configs/base/quality.yaml."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "quality.yaml").write_text(
            """
version: "1.0.0"
thresholds:
  soft_fail: 0.07
  hard_fail: 0.19
strict_validation: false
invalid_record_policy: quarantine
common_field_validations: []
common_cross_field_validations: []
"""
        )

        loader = DQConfigLoader(tmp_path)
        config = loader.load("missing_provider", "missing_entity")
        assert config.soft_fail_threshold == pytest.approx(0.07)
        assert config.hard_fail_threshold == pytest.approx(0.19)

    def test_load_provider_layer_from_unified_provider_file(
        self, tmp_path: Path
    ) -> None:
        """Provider-level DQ rules should load from configs/providers/{provider}.yaml."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "quality.yaml").write_text(
            """
version: "1.0.0"
thresholds:
  soft_fail: 0.05
  hard_fail: 0.20
strict_validation: false
invalid_record_policy: quarantine
common_field_validations: []
common_cross_field_validations: []
"""
        )

        providers_root = tmp_path / "providers"
        providers_root.mkdir(parents=True)
        (providers_root / "test_provider.yaml").write_text(
            """
version: "1.0.0"
provider: test_provider
quality:
  thresholds:
    hard_fail: 0.12
  provider_field_validations:
    - field: provider_field
      type: required
      nullable: true
"""
        )

        loader = DQConfigLoader(tmp_path)
        config = loader.load("test_provider", "missing_entity")
        assert config.hard_fail_threshold == pytest.approx(0.12)
        assert "provider_field" in [fv.field for fv in config.field_validations]

    def test_load_entity_layer_from_unified_entity_file(self, tmp_path: Path) -> None:
        """Entity-level DQ rules should load from configs/entities/{p}/{e}.yaml."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "quality.yaml").write_text(
            """
version: "1.0.0"
thresholds:
  soft_fail: 0.05
  hard_fail: 0.20
strict_validation: false
invalid_record_policy: quarantine
field_validations: []
cross_field_validations: []
"""
        )

        entities_root = tmp_path / "entities" / "test_provider"
        entities_root.mkdir(parents=True)
        (entities_root / "test_entity.yaml").write_text(
            """
version: "1.0.0"
provider: test_provider
entity: test_entity
quality:
  entity_field_validations:
    - field: entity_field
      type: required
      nullable: false
"""
        )

        loader = DQConfigLoader(tmp_path)
        config = loader.load("test_provider", "test_entity")
        assert "entity_field" in [fv.field for fv in config.field_validations]


class TestDQConfigLoaderMerge:
    """Tests for merge behavior in DQConfigLoader."""

    def test_threshold_override(self, loader: DQConfigLoader) -> None:
        """Provider thresholds should override defaults."""
        config = loader.load("test_provider", "unknown_entity")

        # soft_fail same, hard_fail overridden
        assert config.soft_fail_threshold == pytest.approx(0.05)
        assert config.hard_fail_threshold == pytest.approx(0.15)

    def test_field_validations_concatenate(self, loader: DQConfigLoader) -> None:
        """Field validations should concatenate from all levels."""
        config = loader.load("test_provider", "test_entity")

        field_names = [fv.field for fv in config.field_validations]
        assert "_content_hash" in field_names  # common
        assert "common_field" in field_names  # common
        assert "provider_field" in field_names  # provider
        assert "entity_field" in field_names  # entity

    def test_cross_field_validations_merge(self, loader: DQConfigLoader) -> None:
        """Cross-field validations should merge common + entity."""
        config = loader.load("test_provider", "test_entity")

        assert len(config.cross_field_validations) == 1
        assert config.cross_field_validations[0].name == "test_cross"


class TestDQConfigLoaderInlineOverrides:
    """Tests for inline override handling."""

    def test_inline_override_threshold(self, loader: DQConfigLoader) -> None:
        """Inline overrides should be applied last."""
        config = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={"thresholds": {"hard_fail": 0.25}},
        )

        # Override takes precedence
        assert config.hard_fail_threshold == pytest.approx(0.25)

    def test_inline_override_strict_validation(self, loader: DQConfigLoader) -> None:
        """Inline override for strict_validation."""
        config = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={"strict_validation": True},
        )

        assert config.strict_validation is True

    def test_inline_override_flat_threshold_format(
        self, loader: DQConfigLoader
    ) -> None:
        """Inline overrides with flat threshold format should work."""
        config = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={
                "soft_fail_threshold": 0.08,
                "hard_fail_threshold": 0.30,
            },
        )

        assert config.soft_fail_threshold == pytest.approx(0.08)
        assert config.hard_fail_threshold == pytest.approx(0.30)

    def test_inline_override_additional_validations(
        self, loader: DQConfigLoader
    ) -> None:
        """Inline validations should be added to entity level."""
        config = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={
                "entity_field_validations": [
                    {"field": "inline_field", "type": "required", "nullable": False}
                ]
            },
        )

        field_names = [fv.field for fv in config.field_validations]
        assert "inline_field" in field_names

    def test_inline_override_key_nullability_rules(
        self, loader: DQConfigLoader
    ) -> None:
        """Inline key nullability rules should be normalized and merged."""
        config = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={
                "key_nullability": [
                    {
                        "field": "partition_col",
                        "key_type": "partition",
                        "nullable": True,
                    }
                ]
            },
        )

        rules = {
            (r.field, r.key_type, r.nullable) for r in config.key_nullability_rules
        }
        assert ("partition_col", "partition", True) in rules


class TestDQConfigLoaderCaching:
    """Tests for caching behavior."""

    def test_caching_same_config(self, loader: DQConfigLoader) -> None:
        """Same config should be cached."""
        config1 = loader.load("test_provider", "test_entity")
        config2 = loader.load("test_provider", "test_entity")

        assert config1 is config2  # Same object from cache

    def test_no_cache_with_overrides(self, loader: DQConfigLoader) -> None:
        """Configs with overrides should not be cached."""
        config1 = loader.load("test_provider", "test_entity")
        config2 = loader.load(
            "test_provider",
            "test_entity",
            inline_overrides={"strict_validation": True},
        )

        assert config1 is not config2

    def test_clear_cache(self, loader: DQConfigLoader) -> None:
        """clear_cache() should invalidate cache."""
        config1 = loader.load("test_provider", "test_entity")
        loader.clear_cache()
        config2 = loader.load("test_provider", "test_entity")

        assert config1 is not config2

    def test_different_providers_different_cache(self, loader: DQConfigLoader) -> None:
        """Different providers should have separate cache entries."""
        config1 = loader.load("test_provider", "test_entity")
        config2 = loader.load("other_provider", "test_entity")

        assert config1 is not config2


class TestDQConfigLoaderErrors:
    """Tests for error handling in DQConfigLoader."""

    def test_missing_defaults_raises(self, tmp_path: Path) -> None:
        """Missing base/quality.yaml should raise FileNotFoundError."""
        loader = DQConfigLoader(tmp_path)

        with pytest.raises(FileNotFoundError, match=r"base/quality\.yaml"):
            loader.load("any_provider", "any_entity")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML should raise appropriate error."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "quality.yaml").write_text(
            """
version: "1.0.0"
thresholds:
  soft_fail: 0.05
  hard_fail: invalid_not_a_number
"""
        )

        loader = DQConfigLoader(tmp_path)

        with pytest.raises(Exception):  # Pydantic ValidationError
            loader.load("any", "any")

    def test_invalid_threshold_order_raises(self, tmp_path: Path) -> None:
        """soft_fail >= hard_fail should raise ValidationError."""
        base_root = tmp_path / "base"
        base_root.mkdir(parents=True)
        (base_root / "quality.yaml").write_text(
            """
version: "1.0.0"
thresholds:
  soft_fail: 0.30
  hard_fail: 0.10
"""
        )

        loader = DQConfigLoader(tmp_path)

        with pytest.raises(Exception, match="soft_fail"):
            loader.load("any", "any")


class TestDeepMerge:
    """Tests for _deep_merge logic."""

    def test_scalar_override(self, loader: DQConfigLoader) -> None:
        """Scalars should be overridden."""
        base = {"key": "base_value"}
        override = {"key": "override_value"}

        result = loader._deep_merge(base, override)

        assert result["key"] == "override_value"

    def test_nested_dict_merge(self, loader: DQConfigLoader) -> None:
        """Nested dicts should be merged recursively."""
        base = {"outer": {"inner1": "a", "inner2": "b"}}
        override = {"outer": {"inner2": "c", "inner3": "d"}}

        result = loader._deep_merge(base, override)

        assert result["outer"]["inner1"] == "a"  # preserved
        assert result["outer"]["inner2"] == "c"  # overridden
        assert result["outer"]["inner3"] == "d"  # added

    def test_validation_list_concatenate(self, loader: DQConfigLoader) -> None:
        """Validation lists should concatenate with dedup by (field, type, severity)."""
        base: dict[str, Any] = {
            "entity_field_validations": [
                {"field": "a", "type": "required"},
                {"field": "b", "type": "range"},
            ]
        }
        override: dict[str, Any] = {
            "entity_field_validations": [
                {
                    "field": "b",
                    "type": "pattern",
                },  # Different type → kept alongside range
                {"field": "c", "type": "enum"},  # Add new
            ]
        }

        result = loader._deep_merge(base, override)

        validations = result["entity_field_validations"]
        assert len(validations) == 4
        b_validations = [v for v in validations if v["field"] == "b"]
        assert len(b_validations) == 2
        b_types = {v["type"] for v in b_validations}
        assert b_types == {"range", "pattern"}

    def test_non_validation_list_override(self, loader: DQConfigLoader) -> None:
        """Non-validation lists should be overridden, not concatenated."""
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}

        result = loader._deep_merge(base, override)

        assert result["items"] == [4, 5]

    def test_add_new_keys(self, loader: DQConfigLoader) -> None:
        """New keys in override should be added."""
        base = {"existing": "value"}
        override = {"new_key": "new_value"}

        result = loader._deep_merge(base, override)

        assert result["existing"] == "value"
        assert result["new_key"] == "new_value"

    def test_original_unchanged(self, loader: DQConfigLoader) -> None:
        """Original dicts should not be modified."""
        base = {"key": "original"}
        override = {"key": "changed"}

        loader._deep_merge(base, override)

        assert base["key"] == "original"


class TestMergeValidationLists:
    """Tests for _merge_validation_lists logic."""

    def test_dedupe_by_composite_key(self, loader: DQConfigLoader) -> None:
        """Validations dedup by (field, type, severity), not field alone."""
        base = [
            {"field": "a", "type": "required"},
            {"field": "b", "type": "range"},
        ]
        override = [
            {"field": "b", "type": "pattern"},  # Same field, different type → kept
        ]

        result = loader._merge_validation_lists(base, override)

        assert len(result) == 3
        b_items = [v for v in result if v["field"] == "b"]
        assert len(b_items) == 2
        assert {v["type"] for v in b_items} == {"range", "pattern"}

    def test_dedupe_same_field_type_severity(self, loader: DQConfigLoader) -> None:
        """Same field+type+severity → override wins."""
        base = [
            {"field": "b", "type": "range", "min": 0},
        ]
        override = [
            {"field": "b", "type": "range", "min": 10},  # Same composite key
        ]

        result = loader._merge_validation_lists(base, override)

        assert len(result) == 1
        assert result[0]["min"] == 10  # Override wins

    def test_same_field_different_severity_kept(self, loader: DQConfigLoader) -> None:
        """Same field+type but different severity → both kept."""
        base = [
            {"field": "year", "type": "range", "min": 1500, "max": 2100},
        ]
        override = [
            {"field": "year", "type": "range", "severity": "warn", "min": 1950},
        ]

        result = loader._merge_validation_lists(base, override)

        assert len(result) == 2

    def test_dedupe_by_name(self, loader: DQConfigLoader) -> None:
        """Cross-field validations should be deduped by name."""
        base = [
            {"name": "rule_a", "condition": "all_present"},
            {"name": "rule_b", "condition": "any_present"},
        ]
        override = [
            {"name": "rule_b", "condition": "mutually_exclusive"},
        ]

        result = loader._merge_validation_lists(base, override)

        assert len(result) == 2
        rule_b = next(v for v in result if v["name"] == "rule_b")
        assert rule_b["condition"] == "mutually_exclusive"

    def test_preserve_order(self, loader: DQConfigLoader) -> None:
        """Base items should come before override items (when not deduped)."""
        base = [{"field": "a", "type": "required"}]
        override = [{"field": "b", "type": "required"}]

        result = loader._merge_validation_lists(base, override)

        # Order: a first, then b
        assert result[0]["field"] == "a"
        assert result[1]["field"] == "b"


class TestNormalizeToFileFormat:
    """Tests for _normalize_to_file_format logic."""

    def test_flat_to_nested_thresholds(self, loader: DQConfigLoader) -> None:
        """Flat threshold format should be normalized to nested."""
        merged: dict[str, Any] = {
            "soft_fail_threshold": 0.08,
            "hard_fail_threshold": 0.15,
        }

        result = loader._normalize_to_file_format(merged)

        assert "soft_fail_threshold" not in result
        assert "hard_fail_threshold" not in result
        assert result["thresholds"]["soft_fail"] == pytest.approx(0.08)
        assert result["thresholds"]["hard_fail"] == pytest.approx(0.15)

    def test_flat_validations_to_entity(self, loader: DQConfigLoader) -> None:
        """Canonical entity-level field validations are preserved."""
        merged: dict[str, Any] = {
            "entity_field_validations": [{"field": "test", "type": "required"}]
        }

        result = loader._normalize_to_file_format(merged)

        assert len(result["entity_field_validations"]) == 1

    def test_preserve_existing_entity_validations(self, loader: DQConfigLoader) -> None:
        """Existing entity validations should be preserved when adding flat ones."""
        merged: dict[str, Any] = {
            "entity_field_validations": [{"field": "existing", "type": "range"}],
        }
        merged["entity_field_validations"].append({"field": "new", "type": "required"})

        result = loader._normalize_to_file_format(merged)

        assert len(result["entity_field_validations"]) == 2

    def test_cross_field_normalization(self, loader: DQConfigLoader) -> None:
        """Cross-field validations are preserved at entity level."""
        merged: dict[str, Any] = {
            "entity_cross_field_validations": [
                {"name": "rule", "fields": ["a", "b"], "condition": "all_present"}
            ]
        }

        result = loader._normalize_to_file_format(merged)

        assert len(result["entity_cross_field_validations"]) == 1


def test_dq_loader_reads_base_defaults(tmp_path: Path) -> None:
    """Loader should read defaults from configs/base/quality.yaml."""
    root = tmp_path / "base"
    root.mkdir()
    (root / "quality.yaml").write_text(
        """
version: "1.0.0"
thresholds:
  soft_fail: 0.05
  hard_fail: 0.11
common_field_validations: []
"""
    )

    loader = DQConfigLoader(tmp_path)
    config = loader.load("missing", "missing")
    assert config.hard_fail_threshold == pytest.approx(0.11)
