"""Offline observed-value governance for ChEMBL normalization fields."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.domain.normalization.profiles import (
    CHEMBL_ASSAY_PARAMETERS_PROFILE,
    CHEMBL_ASSAY_PROFILE,
    CHEMBL_MOLECULE_PROFILE,
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
    ObservedValuePolicy("molecule", "molecule_type", ("molecule", "types")),
    ObservedValuePolicy("molecule", "structure_type", ("molecule", "structure_types")),
    ObservedValuePolicy("target", "target_type", ("target", "types")),
    ObservedValuePolicy(
        "publication",
        "publication_type",
        ("publication", "native_doc_types"),
    ),
)

REGISTRY_UNIONS: dict[tuple[str, ...], tuple[tuple[str, ...], ...]] = {
    ("assay", "parameter_standard_type_universe"): (
        ("activity", "standard_types"),
        ("assay", "parameter_standard_types"),
    )
}

PROFILE_BY_ENTITY = {
    "assay": CHEMBL_ASSAY_PROFILE,
    "assay_parameters": CHEMBL_ASSAY_PARAMETERS_PROFILE,
    "molecule": CHEMBL_MOLECULE_PROFILE,
    "target": CHEMBL_TARGET_PROFILE,
}


@pytest.fixture(scope="module")
def chembl_enums() -> dict[str, Any]:
    loaded = yaml.safe_load(ENUM_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def observed_values() -> dict[str, dict[str, list[str]]]:
    loaded = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    values = loaded["observed_values"]
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
    observed_values: dict[str, dict[str, list[str]]],
    policy: ObservedValuePolicy,
) -> None:
    values = frozenset(observed_values[policy.entity][policy.field])
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
    observed_values: dict[str, dict[str, list[str]]],
    policy: ObservedValuePolicy,
) -> None:
    profile = PROFILE_BY_ENTITY[policy.entity]
    rule = profile.rule_for(policy.field)
    assert rule is not None

    for value in observed_values[policy.entity][policy.field]:
        assert rule.normalizer(value) is not None
