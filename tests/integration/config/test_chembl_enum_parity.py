"""Subset-governance tests for ChEMBL enum-backed config values."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(".")
ENUM_PATH = ROOT / "configs/enums/chembl.yaml"
ENTITY_CONFIG_ROOT = ROOT / "configs/entities/chembl"


@dataclass(frozen=True, slots=True)
class EnumPolicy:
    entity: str
    field: str
    registry_path: tuple[str, ...]
    surfaces: frozenset[str] = frozenset(
        {"quality", "silver_filters", "gold_filters", "extraction_params"}
    )
    extraction_param: str | None = None

    @property
    def label(self) -> str:
        return f"chembl_{self.entity}.{self.field}"


ENUM_POLICIES: tuple[EnumPolicy, ...] = (
    EnumPolicy("activity", "standard_type", ("activity", "standard_types")),
    EnumPolicy("activity", "standard_relation", ("activity", "standard_relations")),
    EnumPolicy("activity", "assay_type", ("assay", "types")),
    EnumPolicy(
        "activity",
        "bao_endpoint_mapping_status",
        ("activity", "mapping_statuses"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "activity",
        "bao_format_mapping_status",
        ("activity", "mapping_statuses"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "activity",
        "data_validity_comment",
        ("activity", "data_validity_comments"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "activity",
        "qudt_unit_mapping_status",
        ("activity", "mapping_statuses"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy("activity", "standard_units", ("activity", "standard_units")),
    EnumPolicy(
        "activity",
        "uo_unit_mapping_status",
        ("activity", "mapping_statuses"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy("assay", "assay_type", ("assay", "types")),
    EnumPolicy("assay", "relationship_type", ("assay", "relationship_types")),
    EnumPolicy("assay", "assay_test_type", ("assay", "test_types")),
    EnumPolicy("assay", "assay_category", ("assay", "categories")),
    EnumPolicy("assay", "assay_group", ("assay", "assay_groups")),
    EnumPolicy(
        "assay",
        "confidence_description",
        ("assay", "confidence_descriptions"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay_parameters",
        "type",
        ("assay", "parameter_standard_type_universe"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay_parameters",
        "standard_type",
        ("assay", "parameter_standard_type_universe"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay_parameters",
        "standard_relation",
        ("activity", "standard_relations"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay_parameters",
        "standard_units",
        ("activity", "standard_units"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "molecule",
        "max_phase",
        ("molecule", "max_phase_values"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "molecule",
        "ro3_pass",
        ("molecule", "ro3_pass_values"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy("publication", "publication_type", ("publication", "types")),
    EnumPolicy(
        "publication",
        "doc_type",
        ("publication", "native_doc_types"),
        surfaces=frozenset({"extraction_params"}),
        extraction_param="doc_type",
    ),
    EnumPolicy(
        "publication_term",
        "term_type",
        ("publication_term", "term_types"),
    ),
    EnumPolicy(
        "target_component",
        "component_type",
        ("target", "component_types"),
        surfaces=frozenset({"quality"}),
    ),
)

REGISTRY_UNIONS: dict[tuple[str, ...], tuple[tuple[str, ...], ...]] = {
    ("assay", "parameter_standard_type_universe"): (
        ("activity", "standard_types"),
        ("assay", "parameter_standard_types"),
    )
}

EXACT_DQ_ENUM_POLICIES: tuple[EnumPolicy, ...] = (
    EnumPolicy(
        "activity",
        "standard_type",
        ("activity", "standard_types"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "activity",
        "standard_relation",
        ("activity", "standard_relations"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "activity",
        "standard_units",
        ("activity", "standard_units"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "activity", "assay_type", ("assay", "types"), surfaces=frozenset({"quality"})
    ),
    EnumPolicy(
        "assay", "assay_type", ("assay", "types"), surfaces=frozenset({"quality"})
    ),
    EnumPolicy(
        "assay",
        "assay_test_type",
        ("assay", "test_types"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay",
        "assay_category",
        ("assay", "categories"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay",
        "assay_group",
        ("assay", "assay_groups"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay",
        "relationship_type",
        ("assay", "relationship_types"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay",
        "confidence_description",
        ("assay", "confidence_descriptions"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay_parameters",
        "type",
        ("assay", "parameter_standard_type_universe"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay_parameters",
        "standard_type",
        ("assay", "parameter_standard_type_universe"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay_parameters",
        "standard_relation",
        ("activity", "standard_relations"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "assay_parameters",
        "standard_units",
        ("activity", "standard_units"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "molecule",
        "molecule_type",
        ("molecule", "types"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "molecule",
        "structure_type",
        ("molecule", "structure_types"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "molecule",
        "max_phase",
        ("molecule", "max_phase_values"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "molecule",
        "ro3_pass",
        ("molecule", "ro3_pass_values"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "target", "target_type", ("target", "types"), surfaces=frozenset({"quality"})
    ),
    EnumPolicy(
        "target_component",
        "component_type",
        ("target", "component_types"),
        surfaces=frozenset({"quality"}),
    ),
    EnumPolicy(
        "publication_term",
        "term_type",
        ("publication_term", "term_types"),
        surfaces=frozenset({"quality"}),
    ),
)


@pytest.fixture(scope="module")
def chembl_enums() -> dict[str, Any]:
    loaded = yaml.safe_load(ENUM_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def entity_configs() -> dict[str, dict[str, Any]]:
    configs: dict[str, dict[str, Any]] = {}
    for path in ENTITY_CONFIG_ROOT.glob("*.yaml"):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(loaded, dict)
        configs[path.stem] = loaded
    return configs


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


def _quality_allowed_values(config: dict[str, Any], field: str) -> Iterable[str]:
    for validation in config.get("quality", {}).get("entity_field_validations", []):
        if validation.get("field") == field and "allowed" in validation:
            yield from (str(value) for value in validation["allowed"])


def _filter_column_values(
    config: dict[str, Any], stage: str, field: str
) -> Iterable[str]:
    columns = config.get("filters", {}).get(stage, {}).get("columns", {})
    if field not in columns:
        return ()
    return tuple(str(value) for value in columns[field])


def _split_extraction_value(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, list):
        return tuple(str(part) for part in value)
    return (str(value),)


def _extraction_values(config: dict[str, Any], policy: EnumPolicy) -> Iterable[str]:
    params = config.get("filters", {}).get("extraction_params", {})
    param_name = policy.extraction_param or policy.field
    candidate_names = (param_name, f"{param_name}__in")
    for candidate_name in candidate_names:
        if candidate_name in params:
            yield from _split_extraction_value(params[candidate_name])


def _assert_subset(
    *,
    label: str,
    config_path: str,
    values: Iterable[str],
    registry_values: frozenset[str],
) -> None:
    observed = frozenset(values)
    unknown = observed - registry_values
    assert not unknown, (
        f"{label} has values outside {config_path}: {sorted(unknown)}; "
        f"expected subset of {sorted(registry_values)}"
    )


def _assert_exact_match(
    *,
    label: str,
    config_path: str,
    values: Iterable[str],
    registry_values: frozenset[str],
) -> None:
    observed = frozenset(values)
    assert observed == registry_values, (
        f"{label} must exactly match {config_path}; "
        f"missing={sorted(registry_values - observed)} extra={sorted(observed - registry_values)}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("policy", ENUM_POLICIES, ids=lambda policy: policy.label)
def test_chembl_config_enum_surfaces_are_registry_subsets(
    chembl_enums: dict[str, Any],
    entity_configs: dict[str, dict[str, Any]],
    policy: EnumPolicy,
) -> None:
    config = entity_configs[policy.entity]
    registry_values = _registry_values(chembl_enums, policy.registry_path)
    registry_label = ".".join(policy.registry_path)

    if "quality" in policy.surfaces:
        _assert_subset(
            label=f"{policy.label} quality.entity_field_validations.allowed",
            config_path=registry_label,
            values=_quality_allowed_values(config, policy.field),
            registry_values=registry_values,
        )
    if "silver_filters" in policy.surfaces:
        _assert_subset(
            label=f"{policy.label} filters.silver_filters.columns",
            config_path=registry_label,
            values=_filter_column_values(config, "silver_filters", policy.field),
            registry_values=registry_values,
        )
    if "gold_filters" in policy.surfaces:
        _assert_subset(
            label=f"{policy.label} filters.gold_filters.columns",
            config_path=registry_label,
            values=_filter_column_values(config, "gold_filters", policy.field),
            registry_values=registry_values,
        )
    if "extraction_params" in policy.surfaces:
        _assert_subset(
            label=f"{policy.label} filters.extraction_params",
            config_path=registry_label,
            values=_extraction_values(config, policy),
            registry_values=registry_values,
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    "policy", EXACT_DQ_ENUM_POLICIES, ids=lambda policy: f"exact:{policy.label}"
)
def test_chembl_strict_dq_enum_surfaces_match_registry_exactly(
    chembl_enums: dict[str, Any],
    entity_configs: dict[str, dict[str, Any]],
    policy: EnumPolicy,
) -> None:
    config = entity_configs[policy.entity]
    registry_values = _registry_values(chembl_enums, policy.registry_path)
    registry_label = ".".join(policy.registry_path)

    _assert_exact_match(
        label=f"{policy.label} quality.entity_field_validations.allowed",
        config_path=registry_label,
        values=_quality_allowed_values(config, policy.field),
        registry_values=registry_values,
    )


@pytest.mark.integration
def test_chembl_publication_source_specific_doc_type_surfaces_remain_reviewed_subsets(
    chembl_enums: dict[str, Any],
    entity_configs: dict[str, dict[str, Any]],
) -> None:
    config = entity_configs["publication"]
    global_types = _registry_values(chembl_enums, ("publication", "types"))
    native_doc_types = _registry_values(
        chembl_enums, ("publication", "native_doc_types")
    )

    publication_type_values = frozenset(
        _quality_allowed_values(config, "publication_type")
    )
    extraction_doc_types = frozenset(
        _extraction_values(
            config,
            EnumPolicy(
                "publication",
                "doc_type",
                ("publication", "native_doc_types"),
                surfaces=frozenset({"extraction_params"}),
                extraction_param="doc_type",
            ),
        )
    )

    assert publication_type_values < global_types
    assert publication_type_values == frozenset(
        {"journal-article", "book", "dataset", "patent"}
    )
    assert extraction_doc_types <= native_doc_types
