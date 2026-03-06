"""Unit tests for pipeline configuration normalizers."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.config.pipeline_normalizers import (
    _load_column_groups_config,
    _load_data_schema_config,
    _merge_data_schema_into_config,
    _validate_schema_config,
    apply_pipeline_schema_normalization,
)


class TestLoadColumnGroupsConfig:
    """Tests for _load_column_groups_config."""

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        """Should return None when column_groups file is missing."""
        config_path = tmp_path / "config.yaml"
        result = _load_column_groups_config(config_path, "groups.yaml")
        assert result is None

    def test_file_with_list_format(self, tmp_path: Path) -> None:
        """Should return list when file contains a list."""
        groups = [{"name": "system", "columns": ["id"]}]
        (tmp_path / "groups.yaml").write_text(yaml.safe_dump(groups))
        config_path = tmp_path / "config.yaml"
        result = _load_column_groups_config(config_path, "groups.yaml")
        assert result == groups

    def test_file_with_dict_format(self, tmp_path: Path) -> None:
        """Should extract column_groups from dict format."""
        groups = [{"name": "system", "columns": ["id"]}]
        (tmp_path / "groups.yaml").write_text(yaml.safe_dump({"column_groups": groups}))
        config_path = tmp_path / "config.yaml"
        result = _load_column_groups_config(config_path, "groups.yaml")
        assert result == groups

    def test_file_with_dict_no_column_groups_key(self, tmp_path: Path) -> None:
        """Should return None when dict has no column_groups key."""
        (tmp_path / "groups.yaml").write_text(yaml.safe_dump({"other": "value"}))
        config_path = tmp_path / "config.yaml"
        result = _load_column_groups_config(config_path, "groups.yaml")
        assert result is None

    def test_empty_file_returns_none(self, tmp_path: Path) -> None:
        """Should return None for empty file."""
        (tmp_path / "groups.yaml").write_text("")
        config_path = tmp_path / "config.yaml"
        result = _load_column_groups_config(config_path, "groups.yaml")
        assert result is None


class TestLoadDataSchemaConfig:
    """Tests for _load_data_schema_config."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError when schema file is missing."""
        config_path = tmp_path / "config.yaml"
        with pytest.raises(FileNotFoundError, match="Data schema file not found"):
            _load_data_schema_config(config_path, "schema.yaml")

    def test_loads_full_schema(self, tmp_path: Path) -> None:
        """Should load column_groups, silver, gold, and content_hash."""
        schema = {
            "column_groups": [{"name": "system"}],
            "content_hash": {"fields": ["id"]},
            "silver": {"include_groups": ["system"]},
            "gold": {"include_groups": ["system"]},
        }
        (tmp_path / "schema.yaml").write_text(yaml.safe_dump(schema))
        config_path = tmp_path / "config.yaml"
        result = _load_data_schema_config(config_path, "schema.yaml")
        assert result is not None
        assert "column_groups" in result
        assert "content_hash" in result
        assert "silver" in result
        assert "gold" in result

    def test_empty_schema_returns_none(self, tmp_path: Path) -> None:
        """Should return None for empty schema file."""
        (tmp_path / "schema.yaml").write_text("")
        config_path = tmp_path / "config.yaml"
        result = _load_data_schema_config(config_path, "schema.yaml")
        assert result is None

    def test_partial_schema(self, tmp_path: Path) -> None:
        """Should only include present sections."""
        schema = {"column_groups": [{"name": "system"}]}
        (tmp_path / "schema.yaml").write_text(yaml.safe_dump(schema))
        config_path = tmp_path / "config.yaml"
        result = _load_data_schema_config(config_path, "schema.yaml")
        assert result is not None
        assert "column_groups" in result
        assert "silver" not in result


class TestMergeDataSchemaIntoConfig:
    """Tests for _merge_data_schema_into_config."""

    def test_merges_column_groups(self) -> None:
        """Should merge column_groups into config."""
        config: dict = {}
        data_schema = {"column_groups": [{"name": "system"}]}
        _merge_data_schema_into_config(config, data_schema)
        assert config["column_groups"] == [{"name": "system"}]

    def test_merges_content_hash(self) -> None:
        """Should merge content_hash into config."""
        config: dict = {}
        data_schema = {"content_hash": {"fields": ["id"]}}
        _merge_data_schema_into_config(config, data_schema)
        assert config["content_hash"] == {"fields": ["id"]}

    def test_merges_silver_into_data_schema(self) -> None:
        """Should merge silver config under data_schema key."""
        config: dict = {}
        data_schema = {"silver": {"include_groups": ["system"]}}
        _merge_data_schema_into_config(config, data_schema)
        assert config["data_schema"]["silver"] == {"include_groups": ["system"]}

    def test_merges_gold_into_data_schema(self) -> None:
        """Should merge gold config under data_schema key."""
        config: dict = {}
        data_schema = {"gold": {"include_groups": ["system"]}}
        _merge_data_schema_into_config(config, data_schema)
        assert config["data_schema"]["gold"] == {"include_groups": ["system"]}


class TestValidateSchemaConfig:
    """Tests for _validate_schema_config."""

    def test_valid_schema(self) -> None:
        """Should pass for valid schema with system and business groups."""
        data_schema = {
            "column_groups": [
                {"name": "system", "columns": ["id"]},
                {"name": "business", "columns": ["name"]},
            ],
            "silver": {"include_groups": ["system", "business"]},
            "gold": {"include_groups": ["system", "business"]},
        }
        _validate_schema_config(data_schema, "test.yaml")

    def test_missing_column_groups(self) -> None:
        """Should raise for missing column_groups."""
        data_schema = {
            "silver": {"include_groups": ["system"]},
            "gold": {"include_groups": ["system"]},
        }
        with pytest.raises(ValueError, match="column_groups"):
            _validate_schema_config(data_schema, "test.yaml")

    def test_empty_column_groups(self) -> None:
        """Should raise for empty column_groups."""
        data_schema = {
            "column_groups": [],
            "silver": {"include_groups": ["system"]},
            "gold": {"include_groups": ["system"]},
        }
        with pytest.raises(ValueError, match="column_groups"):
            _validate_schema_config(data_schema, "test.yaml")

    def test_missing_system_group(self) -> None:
        """Should raise when system group is missing."""
        data_schema = {
            "column_groups": [{"name": "business", "columns": ["name"]}],
            "silver": {"include_groups": ["business"]},
            "gold": {"include_groups": ["business"]},
        }
        with pytest.raises(ValueError, match="system and business"):
            _validate_schema_config(data_schema, "test.yaml")

    def test_missing_silver_layer(self) -> None:
        """Should raise when silver layer config is missing."""
        data_schema = {
            "column_groups": [
                {"name": "system", "columns": ["id"]},
                {"name": "business", "columns": ["name"]},
            ],
            "gold": {"include_groups": ["system"]},
        }
        with pytest.raises(ValueError, match="silver"):
            _validate_schema_config(data_schema, "test.yaml")

    def test_empty_include_groups(self) -> None:
        """Should raise when include_groups is empty."""
        data_schema = {
            "column_groups": [
                {"name": "system", "columns": ["id"]},
                {"name": "business", "columns": ["name"]},
            ],
            "silver": {"include_groups": []},
            "gold": {"include_groups": ["system"]},
        }
        with pytest.raises(ValueError, match="include_groups"):
            _validate_schema_config(data_schema, "test.yaml")

    def test_silver_not_dict(self) -> None:
        """Should raise when silver is not a dict."""
        data_schema = {
            "column_groups": [
                {"name": "system", "columns": ["id"]},
                {"name": "business", "columns": ["name"]},
            ],
            "silver": "invalid",
            "gold": {"include_groups": ["system"]},
        }
        with pytest.raises(ValueError, match="silver"):
            _validate_schema_config(data_schema, "test.yaml")


class TestApplyPipelineSchemaNormalization:
    """Tests for apply_pipeline_schema_normalization."""

    def test_entity_config_has_column_groups_returns_early(self) -> None:
        """Should return early when entity_config already has column_groups."""
        config: dict = {}
        entity_config = {"column_groups": [{"name": "system"}]}
        apply_pipeline_schema_normalization(
            config, entity_config=entity_config, config_path=Path(".")
        )
        assert "column_groups" not in config

    def test_unified_schema_applied(self) -> None:
        """Should apply unified_schema when provided."""
        config: dict = {}
        unified_schema = {
            "column_groups": [
                {"name": "system", "columns": ["id"]},
                {"name": "business", "columns": ["name"]},
            ],
            "silver": {"include_groups": ["system", "business"]},
            "gold": {"include_groups": ["system", "business"]},
        }
        apply_pipeline_schema_normalization(
            config,
            entity_config={},
            config_path=Path("."),
            unified_schema=unified_schema,
        )
        assert config["column_groups"] == unified_schema["column_groups"]

    def test_loads_from_data_schema_file(self, tmp_path: Path) -> None:
        """Should load schema from data_schema_file when present."""
        schema = {
            "column_groups": [
                {"name": "system", "columns": ["id"]},
                {"name": "business", "columns": ["name"]},
            ],
            "silver": {"include_groups": ["system", "business"]},
            "gold": {"include_groups": ["system", "business"]},
        }
        (tmp_path / "schema.yaml").write_text(yaml.safe_dump(schema))
        config_path = tmp_path / "config.yaml"
        config: dict = {"data_schema_file": "schema.yaml"}
        apply_pipeline_schema_normalization(
            config, entity_config={}, config_path=config_path
        )
        assert "column_groups" in config

    def test_loads_from_schema_file_fallback(self, tmp_path: Path) -> None:
        """Should load schema from schema_file when data_schema_file is absent."""
        schema = {
            "column_groups": [
                {"name": "system", "columns": ["id"]},
                {"name": "business", "columns": ["name"]},
            ],
            "silver": {"include_groups": ["system", "business"]},
            "gold": {"include_groups": ["system", "business"]},
        }
        (tmp_path / "schema.yaml").write_text(yaml.safe_dump(schema))
        config_path = tmp_path / "config.yaml"
        config: dict = {"schema_file": "schema.yaml"}
        apply_pipeline_schema_normalization(
            config, entity_config={}, config_path=config_path
        )
        assert "column_groups" in config

    def test_loads_column_groups_file_fallback(self, tmp_path: Path) -> None:
        """Should load from column_groups_file as last fallback."""
        groups = [
            {"name": "system", "columns": ["id"]},
            {"name": "business", "columns": ["name"]},
        ]
        (tmp_path / "groups.yaml").write_text(yaml.safe_dump(groups))
        config_path = tmp_path / "config.yaml"
        config: dict = {"column_groups_file": "groups.yaml"}
        apply_pipeline_schema_normalization(
            config, entity_config={}, config_path=config_path
        )
        assert config["column_groups"] == groups

    def test_no_schema_sources_does_nothing(self) -> None:
        """Should do nothing when no schema sources are available."""
        config: dict = {}
        apply_pipeline_schema_normalization(
            config, entity_config={}, config_path=Path(".")
        )
        assert "column_groups" not in config
