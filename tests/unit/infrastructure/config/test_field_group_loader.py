"""Tests for field group YAML loader."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.domain.composite.field_groups import FieldGroupId, FieldGroupRegistry
from bioetl.infrastructure.config.field_group_loader import (
    FieldGroupLoadError,
    load_field_groups,
)


pytestmark = pytest.mark.unit

@pytest.fixture()
def tmp_config(tmp_path: Path) -> Path:
    """Create a minimal valid field group config file."""
    config = {
        "version": "1.0",
        "entity": "publication",
        "provider_order": ["chembl", "crossref"],
        "groups": [
            {
                "id": "id_and_status",
                "display_name": "ID & Status",
                "include_in_gold": True,
                "fields": [
                    {
                        "base_name": "doi",
                        "columns": [
                            "chembl.publication.doi",
                            "crossref.publication.doi",
                        ],
                    },
                ],
            },
            {
                "id": "bibliography",
                "display_name": "Bibliography",
                "include_in_gold": True,
                "fields": [
                    {
                        "base_name": "title",
                        "columns": ["chembl.publication.title"],
                    },
                ],
            },
            {
                "id": "trash",
                "display_name": "Trash",
                "include_in_gold": False,
                "fields": [
                    {
                        "base_name": "content_hash",
                        "columns": ["chembl.publication.content_hash"],
                    },
                ],
            },
        ],
    }
    path = tmp_path / "publication.yaml"
    path.write_text(yaml.dump(config), encoding="utf-8")
    return path


class TestLoadFieldGroups:
    """Tests for load_field_groups function."""

    def test_loads_valid_config(self, tmp_config: Path) -> None:
        registry = load_field_groups(tmp_config)
        assert isinstance(registry, FieldGroupRegistry)
        assert registry.field_count == 3
        assert len(registry.groups) == 3

    def test_load_field_groups__provider_order__bf716b98(self, tmp_config: Path) -> None:
        registry = load_field_groups(tmp_config)
        assert registry.provider_order == ("chembl", "crossref")

    def test_group_lookup(self, tmp_config: Path) -> None:
        registry = load_field_groups(tmp_config)
        assert registry.get_group("doi") == FieldGroupId.ID_AND_STATUS
        assert registry.get_group("title") == FieldGroupId.BIBLIOGRAPHY
        assert registry.get_group("content_hash") == FieldGroupId.TRASH

    def test_gold_filtering(self, tmp_config: Path) -> None:
        registry = load_field_groups(tmp_config)
        assert registry.is_gold_field("doi") is True
        assert registry.is_gold_field("content_hash") is False

    def test_qualified_column_lookup(self, tmp_config: Path) -> None:
        registry = load_field_groups(tmp_config)
        assert (
            registry.get_group("chembl.publication.doi") == FieldGroupId.ID_AND_STATUS
        )
        assert (
            registry.get_group("crossref.publication.doi") == FieldGroupId.ID_AND_STATUS
        )

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Field group config not found"):
            load_field_groups(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml_content(self, tmp_path: Path) -> None:
        path = tmp_path / "invalid.yaml"
        path.write_text("just a string", encoding="utf-8")
        with pytest.raises(FieldGroupLoadError, match="expected dict"):
            load_field_groups(path)

    def test_invalid_groups_type(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text(yaml.dump({"groups": "not_a_list"}), encoding="utf-8")
        with pytest.raises(FieldGroupLoadError, match="expected list"):
            load_field_groups(path)

    def test_missing_group_id(self, tmp_path: Path) -> None:
        config = {
            "groups": [
                {
                    "display_name": "No ID",
                    "fields": [],
                }
            ],
        }
        path = tmp_path / "no_id.yaml"
        path.write_text(yaml.dump(config), encoding="utf-8")
        with pytest.raises(FieldGroupLoadError, match="missing 'id'"):
            load_field_groups(path)

    def test_invalid_group_id(self, tmp_path: Path) -> None:
        config = {
            "groups": [
                {
                    "id": "nonexistent_group",
                    "display_name": "Bad Group",
                    "fields": [],
                }
            ],
        }
        path = tmp_path / "bad_group.yaml"
        path.write_text(yaml.dump(config), encoding="utf-8")
        with pytest.raises(FieldGroupLoadError, match="Invalid"):
            load_field_groups(path)

    def test_missing_field_base_name(self, tmp_path: Path) -> None:
        config = {
            "groups": [
                {
                    "id": "bibliography",
                    "display_name": "Bibliography",
                    "fields": [
                        {"columns": ["chembl.publication.title"]},
                    ],
                }
            ],
        }
        path = tmp_path / "no_base.yaml"
        path.write_text(yaml.dump(config), encoding="utf-8")
        with pytest.raises(FieldGroupLoadError, match="base_name"):
            load_field_groups(path)

    def test_default_provider_order(self, tmp_path: Path) -> None:
        """When provider_order is omitted, defaults are used."""
        config = {
            "groups": [
                {
                    "id": "bibliography",
                    "display_name": "Bibliography",
                    "fields": [{"base_name": "title", "columns": []}],
                }
            ],
        }
        path = tmp_path / "default_order.yaml"
        path.write_text(yaml.dump(config), encoding="utf-8")
        registry = load_field_groups(path)
        assert len(registry.provider_order) == 5  # DEFAULT_PROVIDER_ORDER

    def test_load_field_groups__empty_groups__6bf4f46f(self, tmp_path: Path) -> None:
        config = {"groups": []}
        path = tmp_path / "empty.yaml"
        path.write_text(yaml.dump(config), encoding="utf-8")
        registry = load_field_groups(path)
        assert registry.field_count == 0


class TestLoadRealConfig:
    """Test loading the actual publication.yaml config."""

    @pytest.fixture()
    def real_config_path(self) -> Path:
        return Path("configs/composites/field_groups/publication.yaml")

    def test_real_config_exists(self, real_config_path: Path) -> None:
        assert real_config_path.exists(), (
            f"Expected field group config at {real_config_path}"
        )

    def test_real_config_loads(self, real_config_path: Path) -> None:
        if not real_config_path.exists():
            pytest.skip("Real config not available")
        registry = load_field_groups(real_config_path)
        assert isinstance(registry, FieldGroupRegistry)

    def test_real_config_has_all_groups(self, real_config_path: Path) -> None:
        if not real_config_path.exists():
            pytest.skip("Real config not available")
        registry = load_field_groups(real_config_path)
        # Should have all 9 groups (7 business + system_metadata + trash)
        assert len(registry.groups) == 9

    def test_real_config_field_count(self, real_config_path: Path) -> None:
        if not real_config_path.exists():
            pytest.skip("Real config not available")
        registry = load_field_groups(real_config_path)
        # Should map all 94 base fields from FIELD_TO_GROUP_MAPPING
        assert registry.field_count >= 90  # Allow some flexibility

    def test_real_config_consistency_with_existing_mapping(
        self, real_config_path: Path
    ) -> None:
        """Ensure YAML config is consistent with FIELD_TO_GROUP_MAPPING."""
        if not real_config_path.exists():
            pytest.skip("Real config not available")

        from bioetl.domain.value_objects._publication_field_group_types import (
            FIELD_TO_GROUP_MAPPING,
        )

        registry = load_field_groups(real_config_path)

        # Every field in FIELD_TO_GROUP_MAPPING should be in the registry
        # with the same group assignment
        for field_name, expected_group in FIELD_TO_GROUP_MAPPING.items():
            actual_group = registry.get_group(field_name)
            assert actual_group == expected_group, (
                f"Field '{field_name}': expected {expected_group}, got {actual_group}"
            )
