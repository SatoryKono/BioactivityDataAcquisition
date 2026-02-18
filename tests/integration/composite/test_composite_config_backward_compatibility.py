"""Integration checks for composite YAML backward compatibility in v6."""

from __future__ import annotations

import pytest
import yaml

from bioetl.infrastructure.schemas.composite_config import (
    CompositeConfigFileSchema,
    validate_composite_config_payload,
)


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
    )


def test_new_composite_yaml_validates_against_strict_contract() -> None:
    """New format with explicit composite.version must pass strict schema."""
    payload = yaml.safe_load(_base_composite_yaml(with_version=True))

    schema = CompositeConfigFileSchema.model_validate(payload)

    assert schema.composite.version == "1.0.0"


def test_legacy_composite_yaml_supported_with_deprecation_warning() -> None:
    """Old format (without composite.version) stays compatible during window."""
    payload = yaml.safe_load(_base_composite_yaml(with_version=False))

    with pytest.warns(DeprecationWarning, match="composite.version"):
        schema = validate_composite_config_payload(payload)

    assert schema.composite.version == "1.0.0"
