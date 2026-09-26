# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Contract tests for ChEMBL activity flag normalization policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.normalization.profiles import CHEMBL_ACTIVITY_PROFILE
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader
from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    extract_field_metadata,
)

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]

_ACTIVITY_FLAG_FIELDS = (
    ("standard_flag", False),
    ("potential_duplicate", False),
    ("manual_curation_flag", True),
)


def _activity_flag_dq_rule(field_name: str):
    dq_config = DQConfigLoader(Path("configs")).load("chembl", "activity")
    matches = [
        rule
        for rule in dq_config.field_validations
        if rule.field == field_name and rule.validation_type == "range"
    ]
    assert matches, f"Missing DQ range rule for chembl.activity.{field_name}"
    assert len(matches) == 1, (
        f"Duplicate DQ range rules for chembl.activity.{field_name}"
    )
    return matches[0]


@pytest.mark.parametrize(("field_name", "nullable"), _ACTIVITY_FLAG_FIELDS)
def test_activity_flag_fields_align_profile_schema_and_dq(
    field_name: str,
    nullable: bool,
) -> None:
    """Activity flags must remain canonical 0/1 values across all contracts."""
    rule = CHEMBL_ACTIVITY_PROFILE.rule_for(field_name)
    assert rule is not None
    assert rule.apply("yes") == 1
    assert rule.apply("0") == 0
    assert rule.apply("bad") is None

    schema_field = extract_field_metadata(SILVER_SCHEMAS["chembl_activity"])[field_name]
    assert "int" in schema_field["dtype"].lower()
    assert schema_field["nullable"] is nullable
    assert any(check.get("type") == "isin" for check in schema_field["checks"])

    dq_rule = _activity_flag_dq_rule(field_name)
    assert dq_rule.min_value == 0
    assert dq_rule.max_value == 1
    assert dq_rule.nullable is nullable


def test_activity_ontology_bundles_publish_mapped_bundle_requirements() -> None:
    dq_config = DQConfigLoader(Path("configs")).load("chembl", "activity")

    conditional_rules = {rule.name: rule for rule in dq_config.conditional_validations}
    cross_rules = {rule.name: rule for rule in dq_config.cross_field_validations}

    assert {
        "bao_endpoint_requires_mapping_status",
        "bao_format_requires_mapping_status",
        "uo_unit_requires_mapping_status",
        "qudt_unit_requires_mapping_status",
    } <= set(cross_rules)
    assert {
        "mapped_bao_endpoint_requires_bundle",
        "mapped_bao_format_requires_bundle",
        "mapped_uo_unit_requires_bundle",
        "mapped_qudt_unit_requires_bundle",
    } <= set(conditional_rules)

    expected_cross_fields = {
        "bao_endpoint_requires_mapping_status": (
            "bao_endpoint",
            "bao_endpoint_mapping_status",
        ),
        "bao_format_requires_mapping_status": (
            "bao_format",
            "bao_format_mapping_status",
        ),
        "uo_unit_requires_mapping_status": ("uo_units", "uo_unit_mapping_status"),
        "qudt_unit_requires_mapping_status": ("qudt_units", "qudt_unit_mapping_status"),
    }
    for name, (trigger_field, required_field) in expected_cross_fields.items():
        rule = cross_rules[name]
        assert rule.condition == "conditional_required"
        assert rule.trigger_field == trigger_field
        assert rule.required_field == required_field

    expected_conditional_fields = {
        "mapped_bao_endpoint_requires_bundle": {
            "condition_field": "bao_endpoint_mapping_status",
            "then_fields": {"bao_endpoint_iri", "bao_ontology_version"},
        },
        "mapped_bao_format_requires_bundle": {
            "condition_field": "bao_format_mapping_status",
            "then_fields": {"bao_format_iri", "bao_ontology_version"},
        },
        "mapped_uo_unit_requires_bundle": {
            "condition_field": "uo_unit_mapping_status",
            "then_fields": {"uo_unit_iri", "uo_ontology_version"},
        },
        "mapped_qudt_unit_requires_bundle": {
            "condition_field": "qudt_unit_mapping_status",
            "then_fields": {"qudt_unit_iri", "qudt_ontology_version"},
        },
    }
    for name, expected in expected_conditional_fields.items():
        rule = conditional_rules[name]
        assert rule.condition_field == expected["condition_field"]
        assert rule.condition_operator == "eq"
        assert rule.condition_value == "mapped"
        assert {validation.field for validation in rule.then_validations} == expected[
            "then_fields"
        ]
