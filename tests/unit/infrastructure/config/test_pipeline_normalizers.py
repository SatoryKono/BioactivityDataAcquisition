"""Unit tests for pipeline configuration normalizers."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.config.pipeline_normalizers import (
    _project_schema_fields_into_config,
    _validate_schema_config,
    apply_pipeline_schema_normalization,
)


class TestProjectSchemaFieldsIntoConfig:
    """Tests for _project_schema_fields_into_config."""

    def test_merges_column_groups(self) -> None:
        """Should merge column_groups into config."""
        config: dict = {}
        data_schema = {"column_groups": [{"name": "system"}]}
        _project_schema_fields_into_config(config, data_schema)
        assert config["column_groups"] == [{"name": "system"}]

    def test_merges_content_hash(self) -> None:
        """Should merge content_hash into config."""
        config: dict = {}
        data_schema = {"content_hash": {"fields": ["id"]}}
        _project_schema_fields_into_config(config, data_schema)
        assert config["content_hash"] == {"fields": ["id"]}

    def test_projects_silver_into_data_schema(self) -> None:
        """Should project the Silver layer into runtime data_schema payload."""
        config: dict = {}
        data_schema = {"silver": {"include_groups": ["system"]}}
        _project_schema_fields_into_config(config, data_schema)
        assert config["data_schema"] == {"silver": {"include_groups": ["system"]}}

    def test_projects_gold_into_data_schema(self) -> None:
        """Should project the Gold layer into runtime data_schema payload."""
        config: dict = {}
        data_schema = {"gold": {"include_groups": ["system"]}}
        _project_schema_fields_into_config(config, data_schema)
        assert config["data_schema"] == {"gold": {"include_groups": ["system"]}}


class TestValidateSchemaConfig:
    """Tests for _validate_schema_config."""

    def test_validate_schema_config_accepts_required_groups(self) -> None:
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
        assert [group["name"] for group in data_schema["column_groups"]] == [
            "system",
            "business",
        ]

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

    def test_entity_config_column_groups_no_longer_short_circuit(self) -> None:
        """Entity schema in entity_config does not bypass unified schema normalization."""
        config: dict = {}
        entity_config = {"column_groups": [{"name": "system", "columns": ["id"]}]}
        apply_pipeline_schema_normalization(
            config,
            entity_config=entity_config,
            config_path="unused",
            unified_schema=None,
        )
        assert "column_groups" not in config

    def test_unified_schema_applied(self) -> None:
        """Should project runtime-relevant unified_schema fields when provided."""
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
            config_path="unused",
            unified_schema=unified_schema,
        )
        assert config["column_groups"] == unified_schema["column_groups"]
        assert config["data_schema"] == {
            "column_groups": unified_schema["column_groups"],
            "silver": unified_schema["silver"],
            "gold": unified_schema["gold"],
        }
        assert "content_hash" not in config

    def test_no_schema_sources_does_nothing(self) -> None:
        """Should do nothing when no schema sources are available."""
        config: dict = {}
        apply_pipeline_schema_normalization(
            config, entity_config={}, config_path="unused"
        )
        assert "column_groups" not in config
