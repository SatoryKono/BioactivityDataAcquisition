"""Unit tests for schema_file path resolution in config_loader.

Tests:
- Convention-based default path: ../../schemas/{provider}/{entity_type}.yaml
- FileNotFoundError when schema file does not exist
- Correct loading when schema file exists
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bioetl.infrastructure.config_loader import (
    _apply_file_reference_defaults,
    _load_data_schema_config,
)


@pytest.mark.unit
class TestSchemaFileDefault:
    """Verify convention-based default for schema_file."""

    def test_default_path_uses_two_parent_levels(self) -> None:
        """Default schema_file must be ../../schemas/{provider}/{entity}.yaml."""
        config: dict[str, Any] = {}
        _apply_file_reference_defaults(config, "chembl", "molecule")

        assert config["schema_file"] == "../../schemas/chembl/molecule.yaml"

    def test_explicit_override_not_overwritten(self) -> None:
        """Explicit schema_file in config must not be overwritten by default."""
        config: dict[str, Any] = {
            "schema_file": "custom/path/schema.yaml",
        }
        _apply_file_reference_defaults(config, "chembl", "molecule")

        assert config["schema_file"] == "custom/path/schema.yaml"


@pytest.mark.unit
class TestLoadDataSchemaConfig:
    """Tests for _load_data_schema_config file resolution and loading."""

    def test_missing_file_raises_file_not_found_error(self, tmp_path: Path) -> None:
        """Missing schema_file must raise FileNotFoundError."""
        config_path = tmp_path / "pipelines" / "chembl" / "molecule.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.touch()

        with pytest.raises(FileNotFoundError, match="Data schema file not found"):
            _load_data_schema_config(config_path, "../../schemas/chembl/molecule.yaml")

    def test_existing_file_loads_column_groups(self, tmp_path: Path) -> None:
        """Existing schema_file with column_groups must load correctly."""
        # Create pipeline config path
        config_path = tmp_path / "pipelines" / "chembl" / "molecule.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.touch()

        # Create schema file at the resolved path
        schema_path = tmp_path / "schemas" / "chembl" / "molecule.yaml"
        schema_path.parent.mkdir(parents=True)
        schema_path.write_text(
            "column_groups:\n  - name: identifiers\n    fields: [molecule_id]\n"
        )

        result = _load_data_schema_config(
            config_path, "../../schemas/chembl/molecule.yaml"
        )

        assert result is not None
        assert "column_groups" in result
        assert result["column_groups"][0]["name"] == "identifiers"
        assert result["column_groups"][0]["fields"] == ["molecule_id"]

    def test_existing_file_loads_layer_specific_config(self, tmp_path: Path) -> None:
        """Schema file with silver/gold sections must load layer-specific config."""
        config_path = tmp_path / "pipelines" / "chembl" / "publication.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.touch()

        schema_path = tmp_path / "schemas" / "chembl" / "publication.yaml"
        schema_path.parent.mkdir(parents=True)
        schema_path.write_text(
            "column_groups:\n"
            "  - name: identifiers\n"
            "    fields: [publication_id]\n"
            "silver:\n"
            "  include_all_groups: true\n"
            "gold:\n"
            "  exclude_groups:\n"
            "    - complex_fields\n"
        )

        result = _load_data_schema_config(
            config_path, "../../schemas/chembl/publication.yaml"
        )

        assert result is not None
        assert "column_groups" in result
        assert "silver" in result
        assert result["silver"]["include_all_groups"] is True
        assert "gold" in result
        assert result["gold"]["exclude_groups"] == ["complex_fields"]

    def test_empty_schema_file_returns_none(self, tmp_path: Path) -> None:
        """Schema file with no recognized keys must return None."""
        config_path = tmp_path / "pipelines" / "test" / "entity.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.touch()

        schema_path = tmp_path / "schemas" / "test" / "entity.yaml"
        schema_path.parent.mkdir(parents=True)
        schema_path.write_text("version: '1.0.0'\n")

        result = _load_data_schema_config(config_path, "../../schemas/test/entity.yaml")

        assert result is None

    def test_error_message_includes_resolved_path(self, tmp_path: Path) -> None:
        """FileNotFoundError message must include the resolved absolute path."""
        config_path = tmp_path / "pipelines" / "chembl" / "molecule.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.touch()

        with pytest.raises(FileNotFoundError, match=str(tmp_path)):
            _load_data_schema_config(config_path, "../../schemas/chembl/molecule.yaml")
