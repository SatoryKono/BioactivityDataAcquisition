"""Contract tests for strict ChEMBL enum normalization policy."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ASSAY_PROFILE,
    CHEMBL_MOLECULE_PROFILE,
    CHEMBL_TARGET_PROFILE,
)
from bioetl.domain.schemas.constants import (
    ACTIVITY_STANDARD_TYPES,
    ASSAY_CATEGORIES,
    ASSAY_GROUPS,
    ASSAY_TEST_TYPES,
    ASSAY_TYPES,
    CONFIDENCE_DESCRIPTIONS,
    DATA_VALIDITY_COMMENTS,
    MOLECULE_TYPES,
    RELATIONSHIP_TYPES,
    STANDARD_RELATIONS,
    STRUCTURE_TYPES,
    TARGET_TYPES,
)
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader
from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    extract_field_metadata,
)

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]

_STRICT_CHEMBL_ENUM_POLICY = {
    ("activity", "standard_relation"): (
        STANDARD_RELATIONS,
        CHEMBL_ACTIVITY_PROFILE,
        "chembl_activity",
    ),
    ("activity", "standard_type"): (
        ACTIVITY_STANDARD_TYPES,
        CHEMBL_ACTIVITY_PROFILE,
        "chembl_activity",
    ),
    ("activity", "assay_type"): (
        ASSAY_TYPES,
        CHEMBL_ACTIVITY_PROFILE,
        "chembl_activity",
    ),
    ("activity", "data_validity_comment"): (
        DATA_VALIDITY_COMMENTS,
        CHEMBL_ACTIVITY_PROFILE,
        "chembl_activity",
    ),
    ("assay", "assay_type"): (ASSAY_TYPES, CHEMBL_ASSAY_PROFILE, "chembl_assay"),
    ("assay", "assay_test_type"): (
        ASSAY_TEST_TYPES,
        CHEMBL_ASSAY_PROFILE,
        "chembl_assay",
    ),
    ("assay", "assay_category"): (
        ASSAY_CATEGORIES,
        CHEMBL_ASSAY_PROFILE,
        "chembl_assay",
    ),
    ("assay", "assay_group"): (ASSAY_GROUPS, CHEMBL_ASSAY_PROFILE, "chembl_assay"),
    ("assay", "relationship_type"): (
        RELATIONSHIP_TYPES,
        CHEMBL_ASSAY_PROFILE,
        "chembl_assay",
    ),
    ("assay", "confidence_description"): (
        CONFIDENCE_DESCRIPTIONS,
        CHEMBL_ASSAY_PROFILE,
        "chembl_assay",
    ),
    ("molecule", "molecule_type"): (
        MOLECULE_TYPES,
        CHEMBL_MOLECULE_PROFILE,
        "chembl_molecule",
    ),
    ("molecule", "structure_type"): (
        STRUCTURE_TYPES,
        CHEMBL_MOLECULE_PROFILE,
        "chembl_molecule",
    ),
    ("target", "target_type"): (TARGET_TYPES, CHEMBL_TARGET_PROFILE, "chembl_target"),
}

_FILTER_ENUM_POLICY = {
    ("activity", "standard_relation"): STANDARD_RELATIONS,
    ("activity", "standard_type"): ACTIVITY_STANDARD_TYPES,
    ("activity", "assay_type"): ASSAY_TYPES,
    ("assay", "assay_type"): ASSAY_TYPES,
    ("assay", "relationship_type"): RELATIONSHIP_TYPES,
    ("molecule", "molecule_type"): MOLECULE_TYPES,
    ("molecule", "structure_type"): STRUCTURE_TYPES,
    ("target", "target_type"): TARGET_TYPES,
}


def _dq_enum_allowed(entity: str, field_name: str) -> frozenset[str]:
    dq_config = DQConfigLoader(Path("configs")).load("chembl", entity)
    matches = [
        rule
        for rule in dq_config.field_validations
        if rule.field == field_name and rule.validation_type == "enum"
    ]
    assert matches, f"Missing DQ enum rule for chembl.{entity}.{field_name}"
    assert len(matches) == 1, (
        f"Duplicate DQ enum rules for chembl.{entity}.{field_name}"
    )
    return frozenset(matches[0].allowed)


def _schema_has_isin(schema_name: str, field_name: str) -> bool:
    fields = extract_field_metadata(SILVER_SCHEMAS[schema_name])
    checks = fields[field_name].get("checks", [])
    return any(check.get("type") == "isin" for check in checks)


def _load_chembl_entity_config(entity: str) -> dict[str, object]:
    config_path = Path("configs") / "entities" / "chembl" / f"{entity}.yaml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _filter_value_set(raw_values: object) -> frozenset[str]:
    if raw_values is None:
        return frozenset()
    if isinstance(raw_values, str):
        return frozenset(
            value for value in (v.strip() for v in raw_values.split(",")) if value
        )
    if isinstance(raw_values, (list, tuple, set)):
        return frozenset(
            value for value in (str(v).strip() for v in raw_values) if value
        )
    return frozenset({str(raw_values).strip()})


def _enum_filter_values(config: dict[str, object], field_name: str) -> frozenset[str]:
    filters = config.get("filters") or {}
    assert isinstance(filters, dict)

    values: set[str] = set()
    extraction_params = filters.get("extraction_params") or {}
    assert isinstance(extraction_params, dict)
    values.update(_filter_value_set(extraction_params.get(field_name)))
    values.update(_filter_value_set(extraction_params.get(f"{field_name}__in")))

    for filter_key in ("silver_filters", "gold_filters"):
        filter_config = filters.get(filter_key) or {}
        assert isinstance(filter_config, dict)
        columns = filter_config.get("columns") or {}
        assert isinstance(columns, dict)
        values.update(_filter_value_set(columns.get(field_name)))

    return frozenset(values)


@pytest.mark.parametrize(
    ("entity", "field_name"),
    sorted(_STRICT_CHEMBL_ENUM_POLICY),
)
def test_strict_chembl_enum_fields_share_profile_schema_and_dq_policy(
    entity: str,
    field_name: str,
) -> None:
    """Strict ChEMBL enum fields must be governed in profiles, schema, and DQ."""
    allowed_values, profile, schema_name = _STRICT_CHEMBL_ENUM_POLICY[
        (entity, field_name)
    ]

    rule = profile.rule_for(field_name)
    assert rule is not None, (
        f"Missing normalization rule for chembl.{entity}.{field_name}"
    )
    assert rule.normalizer("__BIOETL_INVALID_ENUM__") is None
    assert rule.normalizer(next(iter(allowed_values))) in allowed_values

    assert _schema_has_isin(schema_name, field_name), (
        f"Missing Pandera isin check for {schema_name}.{field_name}"
    )
    assert _dq_enum_allowed(entity, field_name) == allowed_values


@pytest.mark.parametrize(("entity", "field_name"), sorted(_FILTER_ENUM_POLICY))
def test_chembl_filter_enum_values_are_canonical_operational_subsets(
    entity: str,
    field_name: str,
) -> None:
    """Operational filters may narrow enums, but must not define ad-hoc values."""
    allowed_values = _FILTER_ENUM_POLICY[(entity, field_name)]

    filter_values = _enum_filter_values(_load_chembl_entity_config(entity), field_name)

    assert filter_values, f"Missing operational filter for chembl.{entity}.{field_name}"
    assert filter_values <= allowed_values, (
        f"Filter values for chembl.{entity}.{field_name} must stay within the "
        f"canonical enum set: {sorted(filter_values - allowed_values)}"
    )
