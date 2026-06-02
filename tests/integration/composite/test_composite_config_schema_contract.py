"""Integration checks for the strict composite YAML schema contract."""

from __future__ import annotations

import yaml
import pytest
from pydantic import ValidationError

from bioetl.infrastructure.schemas.composite_config import (
    CompositeConfigFileSchema,
    validate_composite_config_payload,
)

pytestmark = pytest.mark.integration


def _base_composite_yaml(with_version: bool) -> str:
    version_line = '  version: "1.0.0"\n' if with_version else ""
    return (
        'schema_version: "2.0.0"\n'
        "composite:\n"
        "  name: composite_compat_test\n"
        f"{version_line}"
        "  seed:\n"
        "    pipeline: chembl_publication\n"
        "    output_keys: [publication_id, doi]\n"
        "    silver_table: silver/chembl/publication\n"
        "  enrichers:\n"
        "    - pipeline: crossref_publication\n"
        "      join_keys: [doi]\n"
        "  merge:\n"
        "    output:\n"
        "      silver: silver/composite/publication\n"
        "      gold: gold/composite/publication\n"
        "    sort_by:\n"
        "      silver: [entity_id, publication_id]\n"
        "      gold: [entity_id, publication_id]\n"
    )


def test_new_composite_yaml_validates_against_strict_contract() -> None:
    """New format with explicit composite.version must pass strict schema."""
    payload = yaml.safe_load(_base_composite_yaml(with_version=True))

    schema = CompositeConfigFileSchema.model_validate(payload)

    assert schema.composite.version == "1.0.0"


def test_composite_yaml_without_version_is_rejected() -> None:
    """Composite configs without explicit version must stay rejected."""
    payload = yaml.safe_load(_base_composite_yaml(with_version=False))

    with pytest.raises(ValidationError, match="version"):
        validate_composite_config_payload(payload)


def test_composite_local_gold_filters_are_rejected() -> None:
    """Top-level composite gold_filters must not drift ahead of runtime support."""
    payload = yaml.safe_load(
        _base_composite_yaml(with_version=True)
        + "gold_filters:\n"
        + "  required_fields: [title]\n"
    )

    with pytest.raises(
        ValidationError,
        match="Composite-local top-level gold_filters are unsupported",
    ):
        validate_composite_config_payload(payload)
