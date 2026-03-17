"""Architecture guardrails for canonical vs compatibility config schema fields."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = PROJECT_ROOT / "configs" / "_schema"


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def test_pipeline_schema_does_not_advertise_retired_file_reference_keys() -> None:
    """Pipeline JSON schema must not expose retired legacy file-reference keys."""
    schema = _load_schema("pipeline.json")
    properties = schema.get("properties")
    assert isinstance(properties, dict), (
        "pipeline.json must contain top-level properties"
    )

    retired_keys = {
        "schema_file",
        "data_schema_file",
        "column_groups_file",
        "primary_keys",
    }
    present = sorted(retired_keys.intersection(properties))
    assert not present, (
        f"pipeline.json still advertises retired legacy file-reference keys: {present}"
    )


def test_pipeline_schema_marks_filter_batch_size_as_deprecated_transition() -> None:
    """Transitional filter_batch_size must stay explicitly deprecated."""
    schema = _load_schema("pipeline.json")
    properties = schema["properties"]
    filter_batch_size = properties.get("filter_batch_size")

    assert isinstance(filter_batch_size, dict), (
        "pipeline.json is missing filter_batch_size property"
    )
    assert filter_batch_size.get("deprecated") is True, (
        "pipeline.filter_batch_size must be marked deprecated=true "
        "as transitional migration-only field"
    )


def test_source_schema_marks_legacy_pagination_aliases_as_deprecated() -> None:
    """Legacy source pagination aliases must be migration-only in JSON schema."""
    schema = _load_schema("source.json")
    defs = schema.get("$defs")
    assert isinstance(defs, dict), "source.json must contain $defs section"

    provider_cfg = defs.get("ProviderConfigYaml")
    assert isinstance(provider_cfg, dict), "source.json missing ProviderConfigYaml"

    properties = provider_cfg.get("properties")
    assert isinstance(properties, dict), "ProviderConfigYaml must define properties"

    for key in ("batch_size", "page_size", "max_url_length"):
        field = properties.get(key)
        assert isinstance(field, dict), (
            f"ProviderConfigYaml must keep {key} as explicit migration alias"
        )
        assert field.get("deprecated") is True, (
            f"ProviderConfigYaml.{key} must be marked deprecated=true"
        )


def test_composite_schema_marks_column_groups_file_as_deprecated() -> None:
    """Composite legacy merge.column_groups_file must remain explicitly deprecated."""
    schema = _load_schema("composite.json")
    defs = schema.get("$defs")
    assert isinstance(defs, dict), "composite.json must contain $defs section"

    merge_schema = defs.get("MergeSchema")
    assert isinstance(merge_schema, dict), "composite.json missing MergeSchema"

    properties = merge_schema.get("properties")
    assert isinstance(properties, dict), "MergeSchema must define properties"

    column_groups_file = properties.get("column_groups_file")
    assert isinstance(column_groups_file, dict), (
        "MergeSchema must keep column_groups_file for compatibility migration seam"
    )
    assert column_groups_file.get("deprecated") is True, (
        "composite.merge.column_groups_file must be marked deprecated=true"
    )
