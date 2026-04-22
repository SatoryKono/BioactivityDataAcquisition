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
