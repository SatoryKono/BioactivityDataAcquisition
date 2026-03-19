"""Unit tests for canonical file-reference defaults in config_loader."""

from __future__ import annotations

from typing import Any

import pytest

from bioetl.infrastructure.config.pipeline_payload_normalization import (
    _apply_file_reference_defaults,
)


@pytest.mark.unit
class TestSchemaFileDefault:
    """Verify deprecated schema-file aliases are no longer injected."""

    def test_no_legacy_schema_file_defaults(self) -> None:
        """Legacy schema-file default aliases are not injected by convention defaults."""
        config: dict[str, Any] = {}
        _apply_file_reference_defaults(config, "chembl", "molecule")

        assert "schema_file" not in config
        assert "column_groups_file" not in config
        assert "data_schema_file" not in config

    def test_defaults_still_include_dq_and_filter_references(self) -> None:
        """Core convention defaults still inject DQ/filter refs."""
        config: dict[str, Any] = {}
        _apply_file_reference_defaults(config, "chembl", "molecule")

        assert config["dq_config_file"] == "../../entities/chembl/molecule.yaml"
        assert config["filter_config_file"] == "../../entities/chembl/molecule.yaml"
