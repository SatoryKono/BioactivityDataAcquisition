"""Contract tests for ChEMBL ontology companion-bundle DQ policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]

_EXPECTED_BUNDLE_RULES = {
    ("assay", "bao_format"): (
        "bao_format_mapping_status",
        "bao_format_iri",
        "bao_ontology_version",
    ),
    ("tissue", "bto_id"): (
        "bto_mapping_status",
        "bto_iri",
        "bto_ontology_version",
    ),
    ("tissue", "efo_id"): (
        "efo_mapping_status",
        "efo_iri",
        "efo_ontology_version",
    ),
    ("tissue", "uberon_id"): (
        "uberon_mapping_status",
        "uberon_iri",
        "uberon_ontology_version",
    ),
    ("cell_line", "clo_id"): (
        "clo_mapping_status",
        "clo_iri",
        "clo_ontology_version",
    ),
    ("cell_line", "efo_id"): (
        "efo_mapping_status",
        "efo_iri",
        "efo_ontology_version",
    ),
}


@pytest.mark.parametrize(
    ("entity", "id_field"),
    sorted(_EXPECTED_BUNDLE_RULES),
)
def test_non_activity_ontology_bundles_publish_mapping_status_and_bundle_rules(
    entity: str,
    id_field: str,
) -> None:
    dq_config = DQConfigLoader(Path("configs")).load("chembl", entity)
    status_field, iri_field, version_field = _EXPECTED_BUNDLE_RULES[(entity, id_field)]

    cross_rule_name = f"{id_field}_requires_mapping_status"
    conditional_rule_name = f"mapped_{id_field}_requires_bundle"
    cross_rules = {rule.name: rule for rule in dq_config.cross_field_validations}
    conditional_rules = {rule.name: rule for rule in dq_config.conditional_validations}

    assert cross_rule_name in cross_rules
    cross_rule = cross_rules[cross_rule_name]
    assert cross_rule.condition == "conditional_required"
    assert cross_rule.trigger_field == id_field
    assert cross_rule.required_field == status_field

    assert conditional_rule_name in conditional_rules
    conditional_rule = conditional_rules[conditional_rule_name]
    assert conditional_rule.condition_field == status_field
    assert conditional_rule.condition_operator == "eq"
    assert conditional_rule.condition_value == "mapped"
    assert {validation.field for validation in conditional_rule.then_validations} == {
        iri_field,
        version_field,
    }
