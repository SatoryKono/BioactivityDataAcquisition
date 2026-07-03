"""Executable parity checks between ChEMBL DQ rules and normalization profiles."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.domain.normalization.profiles import resolve_normalization_profile

_CONFIG_ROOT = Path("configs/entities/chembl")


def _load_entity_config(entity_type: str) -> dict[str, Any]:
    payload = yaml.safe_load(
        (_CONFIG_ROOT / f"{entity_type}.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(payload, dict)
    return payload


def _find_field_validation(payload: object, field_name: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        if payload.get("field") == field_name:
            return payload
        for value in payload.values():
            found = _find_field_validation(value, field_name)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _find_field_validation(item, field_name)
            if found:
                return found
    return {}


@pytest.mark.integration
@pytest.mark.parametrize(
    ("entity_type", "field_name", "raw_value"),
    [
        ("activity", "standard_relation", "<="),
        ("activity", "standard_units", "uM"),
        ("activity", "standard_flag", "1"),
        ("assay_parameters", "standard_relation", ">="),
        ("assay_parameters", "standard_units", "uM"),
        ("molecule", "molecule_type", "protein"),
        ("molecule", "black_box_warning", "1"),
        ("target", "target_type", "single protein"),
        ("target_component", "component_type", "protein"),
        ("publication_term", "term_type", "mesh_heading"),
    ],
)
def test_profile_outputs_satisfy_declared_chembl_dq_surface(
    entity_type: str,
    field_name: str,
    raw_value: str,
) -> None:
    """Representative normalized values must satisfy the declared DQ contract."""
    config = _load_entity_config(entity_type)
    validation = _find_field_validation(config, field_name)
    profile = resolve_normalization_profile("chembl", entity_type)

    assert validation, f"Missing validation for {entity_type}.{field_name}"
    assert profile is not None
    rule = profile.rule_for(field_name)
    assert rule is not None

    normalized = rule.apply(raw_value)
    assert normalized is not None

    validation_type = validation.get("type")
    if validation_type == "enum":
        allowed = {str(value) for value in validation.get("allowed", [])}
        assert str(normalized) in allowed
        return
    if validation_type == "range":
        assert float(validation["min"]) <= float(normalized) <= float(validation["max"])
        return
    if validation_type == "pattern":
        assert re.match(str(validation["pattern"]), str(normalized))
        return

    pytest.fail(f"Unsupported validation type for {entity_type}.{field_name}")


@pytest.mark.integration
@pytest.mark.parametrize(
    ("entity_type", "field_name", "invalid_value"),
    [
        ("activity", "standard_units", "made_up_unit"),
        ("publication_term", "term_type", "not_a_term_type"),
    ],
)
def test_invalid_values_do_not_sneak_through_profile_and_dq_contract(
    entity_type: str,
    field_name: str,
    invalid_value: str,
) -> None:
    """Known invalid values must not silently normalize into accepted DQ values."""
    profile = resolve_normalization_profile("chembl", entity_type)
    assert profile is not None
    rule = profile.rule_for(field_name)
    assert rule is not None

    normalized = rule.apply(invalid_value)
    assert normalized is None
