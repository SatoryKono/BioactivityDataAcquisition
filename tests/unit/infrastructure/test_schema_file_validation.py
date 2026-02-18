from __future__ import annotations

import pytest

from bioetl.infrastructure.config_loader import _validate_schema_config


@pytest.mark.unit
def test_validate_schema_config_accepts_minimum_structure() -> None:
    schema = {
        "column_groups": [
            {"name": "system", "fields": ["entity_id"]},
            {"name": "identifiers", "fields": ["compound_id"]},
            {"name": "business", "pattern": "^name$"},
        ],
        "silver": {"include_groups": ["system", "identifiers", "business"]},
        "gold": {"include_groups": ["system", "identifiers"]},
    }

    _validate_schema_config(schema, "../../schemas/test/entity.yaml")


@pytest.mark.unit
def test_validate_schema_config_rejects_empty_column_groups() -> None:
    schema = {
        "column_groups": [],
        "silver": {"include_groups": ["system"]},
        "gold": {"include_groups": ["system"]},
    }

    with pytest.raises(ValueError, match="non-empty column_groups"):
        _validate_schema_config(schema, "../../schemas/test/entity.yaml")
