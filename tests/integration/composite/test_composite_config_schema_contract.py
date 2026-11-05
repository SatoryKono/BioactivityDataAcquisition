# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration checks for the strict composite YAML schema contract."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest
from pydantic import ValidationError

from bioetl.application.composite.helpers.preflight_type_and_aggregation import (
    validate_aggregation_ordering,
)
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
        "      cardinality: many_to_one\n"
        "      aggregation:\n"
        "        group_by: doi\n"
        "        order_by: [entity_id]\n"
        "        fields:\n"
        "          authors:\n"
        "            source: authors_list\n"
        "            agg: first\n"
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
    enricher = schema.composite.enrichers[0]
    assert enricher.cardinality == "many_to_one"
    assert enricher.aggregation is not None
    assert enricher.aggregation.group_by == "doi"
    assert enricher.aggregation.order_by == ["entity_id"]
    assert enricher.aggregation.fields["authors"].source == "authors_list"
    assert enricher.aggregation.fields["authors"].agg == "first"
    assert validate_aggregation_ordering(schema.to_domain()) == []


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


def test_composite_many_to_one_enricher_aggregation_is_validated() -> None:
    """MANY_TO_ONE enrichers must explicitly define aggregation rules statically."""
    fixture = Path(__file__).parents[2] / "fixtures/composite/many_to_one_enricher.yaml"
    base = yaml.safe_load(fixture.read_text(encoding="utf-8"))

    # Verify missing aggregation fails
    missing_aggregation = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    del missing_aggregation["composite"]["enrichers"][0]["aggregation"]
    with pytest.raises(ValidationError, match="requires aggregation config"):
        validate_composite_config_payload(missing_aggregation)

    # Verify complete MANY_TO_ONE specification passes
    schema = CompositeConfigFileSchema.model_validate(base)
    assert schema.composite.enrichers[0].cardinality == "many_to_one"
    assert schema.composite.enrichers[0].aggregation is not None
    assert schema.composite.enrichers[0].aggregation.group_by == "doi"


def test_composite_preflight_hash_mismatch() -> None:
    """Composite preflight must fail fast if expected_normalization_profile_hash mismatches."""
    from bioetl.application.composite.preflight_validator import (
        CompositePreflightValidationService,
    )
    from bioetl.application.composite._preflight_types import PreflightValidationError
    from bioetl.infrastructure.schemas.composite_config import CompositeConfigFileSchema
    from unittest.mock import MagicMock
    import yaml

    payload = yaml.safe_load(_base_composite_yaml(with_version=True))
    payload["composite"]["expected_normalization_profile_hash"] = "invalid_hash_abc123"
    schema = CompositeConfigFileSchema.model_validate(payload)
    config = schema.to_domain()

    service = CompositePreflightValidationService(MagicMock())
    service._load_source_profiles = MagicMock(
        return_value={"test_src": MagicMock(profile_hash="hash456")}
    )

    with pytest.raises(PreflightValidationError) as exc:
        service.validate(config)

    assert "Expected composite profile hash 'invalid_hash_abc123'" in str(exc.value)
