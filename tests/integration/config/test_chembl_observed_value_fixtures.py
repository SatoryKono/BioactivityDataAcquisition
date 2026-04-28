"""Offline observed-value governance for ChEMBL normalization fields."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ASSAY_PARAMETERS_PROFILE,
    CHEMBL_ASSAY_PROFILE,
    CHEMBL_CELL_LINE_PROFILE,
    CHEMBL_MOLECULE_PROFILE,
    CHEMBL_PUBLICATION_PROFILE,
    CHEMBL_PUBLICATION_TERM_PROFILE,
    CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
    CHEMBL_TARGET_COMPONENT_PROFILE,
    CHEMBL_TARGET_PROFILE,
)

ROOT = Path(".")
ENUM_PATH = ROOT / "configs" / "enums" / "chembl.yaml"
FIXTURE_PATH = (
    ROOT / "tests" / "fixtures" / "normalization" / "chembl_observed_values.yaml"
)


@dataclass(frozen=True, slots=True)
class ObservedValuePolicy:
    entity: str
    field: str
    registry_path: tuple[str, ...]

    @property
    def label(self) -> str:
        return f"chembl.{self.entity}.{self.field}"


OBSERVED_VALUE_POLICIES: tuple[ObservedValuePolicy, ...] = (
    ObservedValuePolicy(
        "activity",
        "standard_relation",
        ("activity", "standard_relations"),
    ),
    ObservedValuePolicy(
        "activity",
        "standard_units",
        ("activity", "standard_units"),
    ),
    ObservedValuePolicy("assay", "assay_type", ("assay", "types")),
    ObservedValuePolicy("assay", "assay_test_type", ("assay", "test_types")),
    ObservedValuePolicy("assay", "assay_category", ("assay", "categories")),
    ObservedValuePolicy("assay", "assay_group", ("assay", "assay_groups")),
    ObservedValuePolicy("assay", "relationship_type", ("assay", "relationship_types")),
    ObservedValuePolicy(
        "assay",
        "confidence_description",
        ("assay", "confidence_descriptions"),
    ),
    ObservedValuePolicy(
        "assay",
        "assay_subcellular_fraction",
        ("assay", "subcellular_fractions"),
    ),
    ObservedValuePolicy(
        "activity",
        "bao_endpoint_mapping_status",
        ("activity", "mapping_statuses"),
    ),
    ObservedValuePolicy(
        "activity",
        "bao_format_mapping_status",
        ("activity", "mapping_statuses"),
    ),
    ObservedValuePolicy(
        "activity",
        "qudt_unit_mapping_status",
        ("activity", "mapping_statuses"),
    ),
    ObservedValuePolicy(
        "activity",
        "uo_unit_mapping_status",
        ("activity", "mapping_statuses"),
    ),
    ObservedValuePolicy(
        "assay_parameters",
        "standard_type",
        ("assay", "parameter_standard_type_universe"),
    ),
    ObservedValuePolicy(
        "assay_parameters",
        "standard_relation",
        ("activity", "standard_relations"),
    ),
    ObservedValuePolicy(
        "assay_parameters",
        "standard_units",
        ("activity", "standard_units"),
    ),
    ObservedValuePolicy("molecule", "max_phase", ("molecule", "max_phase_values")),
    ObservedValuePolicy("molecule", "molecule_type", ("molecule", "types")),
    ObservedValuePolicy("molecule", "ro3_pass", ("molecule", "ro3_pass_values")),
    ObservedValuePolicy("molecule", "structure_type", ("molecule", "structure_types")),
    ObservedValuePolicy("target", "target_type", ("target", "types")),
    ObservedValuePolicy(
        "target_component",
        "component_type",
        ("target", "component_types"),
    ),
    ObservedValuePolicy(
        "publication",
        "publication_type",
        ("publication", "types"),
    ),
    ObservedValuePolicy(
        "publication_term",
        "term_type",
        ("publication_term", "term_types"),
    ),
)

REGISTRY_UNIONS: dict[tuple[str, ...], tuple[tuple[str, ...], ...]] = {
    ("assay", "parameter_standard_type_universe"): (
        ("activity", "standard_types"),
        ("assay", "parameter_standard_types"),
    )
}

PROFILE_BY_ENTITY = {
    "activity": CHEMBL_ACTIVITY_PROFILE,
    "assay": CHEMBL_ASSAY_PROFILE,
    "assay_parameters": CHEMBL_ASSAY_PARAMETERS_PROFILE,
    "cell_line": CHEMBL_CELL_LINE_PROFILE,
    "molecule": CHEMBL_MOLECULE_PROFILE,
    "publication": CHEMBL_PUBLICATION_PROFILE,
    "subcellular_fraction": CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
    "target": CHEMBL_TARGET_PROFILE,
    "target_component": CHEMBL_TARGET_COMPONENT_PROFILE,
    "publication_term": CHEMBL_PUBLICATION_TERM_PROFILE,
}


@pytest.fixture(scope="module")
def chembl_enums() -> dict[str, Any]:
    loaded = yaml.safe_load(ENUM_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def fixture_payload() -> dict[str, Any]:
    loaded = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def observed_values(fixture_payload: dict[str, Any]) -> dict[str, dict[str, list[Any]]]:
    values = fixture_payload["observed_values"]
    assert isinstance(values, dict)
    return values


@pytest.fixture(scope="module")
def policy_values(fixture_payload: dict[str, Any]) -> dict[str, dict[str, list[Any]]]:
    values = fixture_payload["policy_values"]
    assert isinstance(values, dict)
    return values


@pytest.fixture(scope="module")
def dq_only_subsets(
    fixture_payload: dict[str, Any],
) -> dict[str, dict[str, list[Any]]]:
    values = fixture_payload["dq_only_subsets"]
    assert isinstance(values, dict)
    return values


@pytest.fixture(scope="module")
def unexpected_observed_values(
    fixture_payload: dict[str, Any],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    values = fixture_payload["unexpected_observed_values"]
    assert isinstance(values, dict)
    return values


@pytest.fixture(scope="module")
def negative_values(
    fixture_payload: dict[str, Any],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    values = fixture_payload["negative_values"]
    assert isinstance(values, dict)
    return values


def _registry_values(
    enums: dict[str, Any],
    registry_path: tuple[str, ...],
) -> frozenset[str]:
    union_paths = REGISTRY_UNIONS.get(registry_path)
    if union_paths is not None:
        return frozenset().union(
            *(_registry_values(enums, union_path) for union_path in union_paths)
        )
    current: Any = enums
    for part in registry_path:
        current = current[part]
    assert isinstance(current, list)
    return frozenset(str(value) for value in current)


@pytest.mark.integration
@pytest.mark.parametrize(
    "policy",
    OBSERVED_VALUE_POLICIES,
    ids=lambda policy: policy.label,
)
def test_chembl_observed_values_are_ssot_subsets(
    chembl_enums: dict[str, Any],
    observed_values: dict[str, dict[str, list[Any]]],
    policy: ObservedValuePolicy,
) -> None:
    values = frozenset(
        str(value) for value in observed_values[policy.entity][policy.field]
    )
    registry_values = _registry_values(chembl_enums, policy.registry_path)

    assert values
    assert values <= registry_values, (
        f"{policy.label} observed values outside registry "
        f"{'.'.join(policy.registry_path)}: {sorted(values - registry_values)}"
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "policy",
    [
        policy
        for policy in OBSERVED_VALUE_POLICIES
        if policy.entity in PROFILE_BY_ENTITY
    ],
    ids=lambda policy: policy.label,
)
def test_chembl_observed_values_are_accepted_by_profiles(
    observed_values: dict[str, dict[str, list[Any]]],
    policy: ObservedValuePolicy,
) -> None:
    profile = PROFILE_BY_ENTITY[policy.entity]
    rule = profile.rule_for(policy.field)
    assert rule is not None

    for value in observed_values[policy.entity][policy.field]:
        assert rule.normalizer(value) is not None


@pytest.mark.integration
def test_all_observed_values_are_accepted_by_profiles(
    observed_values: dict[str, dict[str, list[Any]]],
) -> None:
    for entity, fields in observed_values.items():
        profile = PROFILE_BY_ENTITY.get(entity)
        if profile is None:
            continue
        for field, values in fields.items():
            rule = profile.rule_for(field)
            assert rule is not None, f"Missing rule for chembl.{entity}.{field}"
            for value in values:
                assert rule.normalizer(value) is not None, (
                    f"Observed value for chembl.{entity}.{field} should be accepted: "
                    f"{value!r}"
                )


@pytest.mark.integration
def test_policy_values_can_extend_beyond_observed_samples(
    observed_values: dict[str, dict[str, list[Any]]],
    policy_values: dict[str, dict[str, list[Any]]],
) -> None:
    differences = []
    for entity, fields in policy_values.items():
        observed_entity = observed_values.get(entity, {})
        for field, values in fields.items():
            policy_set = frozenset(str(value) for value in values)
            observed_set = frozenset(
                str(value) for value in observed_entity.get(field, [])
            )
            if policy_set - observed_set:
                differences.append((entity, field))

    assert differences, (
        "fixtures should preserve at least one policy-bearing field where the "
        "allowed policy surface is broader than the currently observed sample set"
    )


@pytest.mark.integration
def test_dq_only_subsets_remain_within_declared_policy_sets(
    policy_values: dict[str, dict[str, list[Any]]],
    dq_only_subsets: dict[str, dict[str, list[Any]]],
) -> None:
    for entity, fields in dq_only_subsets.items():
        assert entity in policy_values
        for field, values in fields.items():
            assert field in policy_values[entity]
            dq_values = frozenset(str(value) for value in values)
            policy_set = frozenset(str(value) for value in policy_values[entity][field])
            assert dq_values <= policy_set, (
                f"chembl.{entity}.{field} DQ-only subset exceeds declared policy set: "
                f"{sorted(dq_values - policy_set)}"
            )


def _iter_case_matrix(
    case_mapping: dict[str, dict[str, list[dict[str, Any]]]],
) -> list[tuple[str, str, Any, Any]]:
    rows: list[tuple[str, str, Any, Any]] = []
    for entity, fields in case_mapping.items():
        for field, cases in fields.items():
            for case in cases:
                rows.append((entity, field, case["input"], case["expected"]))
    return rows


@pytest.mark.integration
@pytest.mark.parametrize(
    ("entity", "field", "raw_value", "expected"),
    _iter_case_matrix(
        yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))[
            "unexpected_observed_values"
        ]
    ),
    ids=lambda params: (
        f"chembl.{params[0]}.{params[1]}" if isinstance(params, tuple) else repr(params)
    ),
)
def test_unexpected_observed_values_have_explicit_normalization_behavior(
    entity: str,
    field: str,
    raw_value: Any,
    expected: Any,
) -> None:
    profile = PROFILE_BY_ENTITY[entity]
    rule = profile.rule_for(field)
    assert rule is not None
    assert rule.normalizer(raw_value) == expected


@pytest.mark.integration
@pytest.mark.parametrize(
    ("entity", "field", "raw_value", "expected"),
    _iter_case_matrix(
        yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))["negative_values"]
    ),
    ids=lambda params: (
        f"chembl.{params[0]}.{params[1]}" if isinstance(params, tuple) else repr(params)
    ),
)
def test_negative_values_fail_closed_or_downgrade_deterministically(
    entity: str,
    field: str,
    raw_value: Any,
    expected: Any,
) -> None:
    profile = PROFILE_BY_ENTITY[entity]
    rule = profile.rule_for(field)
    assert rule is not None
    assert rule.normalizer(raw_value) == expected
