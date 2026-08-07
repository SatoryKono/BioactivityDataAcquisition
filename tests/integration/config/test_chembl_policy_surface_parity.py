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
"""Cross-surface parity tests for ChEMBL enum, vocabulary, profile, and DQ policy."""

from __future__ import annotations

from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

import pytest
import yaml

from bioetl.domain.normalization.profiles.chembl_policy_registry import (
    CHEMBL_CONTROLLED_VOCAB_CONFIG,
    CHEMBL_ONTOLOGY_POLICY_CONFIG,
    CHEMBL_REFERENCE_IDENTIFIER_CONFIG,
    DEFAULT_CHEMBL_POLICY_REGISTRY_DATA,
)
from bioetl.domain.normalization.profiles.chembl_assay import CHEMBL_ASSAY_PROFILE
from bioetl.domain.normalization.profiles.chembl_json_ordering_policy import (
    CHEMBL_JSON_ORDERING_POLICY,
)
from bioetl.domain.normalization.profiles.registry import (
    NORMALIZATION_PROFILE_REGISTRY,
)
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from bioetl.infrastructure.config.chembl_policy_registry_loader import (
    ChemblPolicyRegistryLoader,
)
from scripts.docs.matrix.generate_pipeline_normalization_matrix import (
    build_field_matrix_rows,
)
from scripts.docs.matrix.generate_pipeline_normalization_matrix import (
    ENTITY_PROFILE_FIELD_ALIASES,
    ENUM_REGISTRY_PATHS,
)

ROOT = Path(".")
CONFIGS_ROOT = ROOT / "configs"
ENTITY_CONFIG_ROOT = CONFIGS_ROOT / "entities" / "chembl"
CHEMBL_ENUM_PATH = CONFIGS_ROOT / "enums" / "chembl.yaml"

ALLOWED_FIELD_CLASSIFICATIONS = frozenset(
    {
        "strict enum",
        "controlled vocabulary",
        "flag-like",
        "operator",
        "ontology/reference identifier",
        "reference identifier",
        "unit-like",
    }
)


def _load_yaml(path: Path | str) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _parse_field_ref(field_ref: str) -> tuple[str, str]:
    pipeline_name, field_name = field_ref.split(".", maxsplit=1)
    return pipeline_name, field_name


def _normalize_source_path(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix()


def _matrix_row_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup = {
        f"{row['pipeline_name']}.{row['field_name']}": row
        for row in rows
        if row["pipeline_name"].startswith("chembl_")
    }
    for pipeline_name, aliases in ENTITY_PROFILE_FIELD_ALIASES.items():
        if not pipeline_name.startswith("chembl_"):
            continue
        for alias_field, canonical_field in aliases.items():
            canonical_ref = f"{pipeline_name}.{canonical_field}"
            alias_ref = f"{pipeline_name}.{alias_field}"
            if alias_ref not in lookup and canonical_ref in lookup:
                lookup[alias_ref] = lookup[canonical_ref]
    return lookup


def _row_classification(row: dict[str, str]) -> str:
    strictness = row["strictness"]
    semantic_category = row["semantic_category"]
    field_name = row["field_name"]

    if strictness in {"strict_boolean", "strict_flag"}:
        return "flag-like"
    if strictness == "strict_operator":
        return "operator"
    if strictness == "strict_enum":
        return "strict enum"
    if strictness == "controlled_unit" or field_name in {
        "units",
        "standard_units",
        "qudt_units",
        "uo_units",
    }:
        return "unit-like"
    if semantic_category.startswith("ontology_reference"):
        return "ontology/reference identifier"
    if semantic_category == "reference_identifier":
        return "reference identifier"
    if semantic_category == "controlled_vocabulary":
        return "controlled vocabulary"
    raise AssertionError(
        "Unsupported ChEMBL policy classification for "
        f"{row['pipeline_name']}.{row['field_name']}: "
        f"semantic_category={semantic_category!r}, strictness={strictness!r}"
    )


def _registered_chembl_profile_fields(entity: str) -> frozenset[str]:
    profile = NORMALIZATION_PROFILE_REGISTRY.get(("chembl", entity))
    return frozenset() if profile is None else profile.fields


def _registry_governed_field_expectations() -> dict[str, tuple[str, str]]:
    expectations: dict[str, tuple[str, str]] = {}

    for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.strict_boolean_families:
        for field_ref in family.fields:
            expectations[str(field_ref)] = ("flag-like", CHEMBL_CONTROLLED_VOCAB_CONFIG)

    for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.strict_flag_families:
        for field_ref in family.fields:
            expectations[str(field_ref)] = ("flag-like", CHEMBL_CONTROLLED_VOCAB_CONFIG)

    for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.controlled_vocabularies:
        if family.family_name == "operators":
            classification = "operator"
        elif family.family_name == "raw_units":
            classification = "unit-like"
        elif family.family_name == "standard_units":
            classification = "strict enum"
        elif family.family_name == "assay_confidence_descriptions":
            classification = "strict enum"
        elif family.family_name in {
            "publication_oa_statuses",
            "target_organism_classes",
        }:
            classification = "strict enum"
        else:
            classification = "controlled vocabulary"
        for field_ref in family.fields:
            expectations[str(field_ref)] = (
                classification,
                CHEMBL_CONTROLLED_VOCAB_CONFIG,
            )

    for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.ontology_families:
        classification = (
            "unit-like"
            if family.family_name in {"uo", "qudt"}
            else "ontology/reference identifier"
        )
        for field_ref in family.fields + family.iri_fields:
            expectations[str(field_ref)] = (
                classification,
                CHEMBL_ONTOLOGY_POLICY_CONFIG,
            )

    for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.reference_identifier_families:
        for field_ref in family.fields:
            expectations[str(field_ref)] = (
                "reference identifier",
                CHEMBL_REFERENCE_IDENTIFIER_CONFIG,
            )

    return expectations


def _config_enum_surface_expectations(
    entity_configs: dict[str, dict[str, Any]],
) -> dict[str, tuple[str, str]]:
    expectations: dict[str, tuple[str, str]] = {}

    # Get all controlled vocabulary fields to avoid overwriting registry expectations
    controlled_vocabulary_fields = frozenset().union(
        *(
            family.fields
            for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.controlled_vocabularies
        )
    )

    for entity, config in entity_configs.items():
        known_profile_fields = _registered_chembl_profile_fields(entity)
        if not known_profile_fields:
            continue

        validations = config.get("quality", {}).get("entity_field_validations", [])
        for validation in validations:
            if validation.get("type") != "enum":
                continue
            field_name = str(validation.get("field", ""))
            if ("chembl", entity, field_name) not in ENUM_REGISTRY_PATHS:
                continue
            field_ref = f"chembl_{entity}.{field_name}"
            # Skip controlled vocabulary fields - they use CHEMBL_CONTROLLED_VOCAB_CONFIG
            if field_ref in controlled_vocabulary_fields:
                continue
            if field_name in known_profile_fields:
                classification = (
                    "operator" if field_name == "standard_relation" else "strict enum"
                )
                expectations[field_ref] = (
                    classification,
                    CHEMBL_ENUM_PATH.as_posix(),
                )

        filters = config.get("filters", {})
        for stage_name in ("silver_filters", "gold_filters"):
            columns = filters.get(stage_name, {}).get("columns", {})
            for field_name, values in columns.items():
                if ("chembl", entity, str(field_name)) not in ENUM_REGISTRY_PATHS:
                    continue
                field_ref = f"chembl_{entity}.{field_name}"
                # Skip controlled vocabulary fields - they use CHEMBL_CONTROLLED_VOCAB_CONFIG
                if field_ref in controlled_vocabulary_fields:
                    continue
                if field_name not in known_profile_fields:
                    continue
                if isinstance(values, dict):
                    values = values.get("values")
                if not isinstance(values, list):
                    continue
                if any(isinstance(value, (dict, list)) for value in values):
                    continue
                classification = (
                    "operator" if field_name == "standard_relation" else "strict enum"
                )
                expectations[field_ref] = (
                    classification,
                    CHEMBL_ENUM_PATH.as_posix(),
                )

        extraction_params = filters.get("extraction_params", {})
        for raw_name, value in extraction_params.items():
            field_name = str(raw_name).removesuffix("__in")
            if ("chembl", entity, field_name) not in ENUM_REGISTRY_PATHS:
                continue
            field_ref = f"chembl_{entity}.{field_name}"
            # Skip controlled vocabulary fields - they use CHEMBL_CONTROLLED_VOCAB_CONFIG
            if field_ref in controlled_vocabulary_fields:
                continue
            if field_name not in known_profile_fields:
                continue
            if not isinstance(value, (str, int, float, list)):
                continue
            classification = (
                "operator" if field_name == "standard_relation" else "strict enum"
            )
            expectations[f"chembl_{entity}.{field_name}"] = (
                classification,
                CHEMBL_ENUM_PATH.as_posix(),
            )

    return expectations


def _entity_field_validation(
    entity_config: dict[str, Any],
    field_name: str,
) -> dict[str, Any]:
    for validation in entity_config.get("quality", {}).get(
        "entity_field_validations", []
    ):
        if validation.get("field") == field_name:
            return validation
    raise AssertionError(f"Missing entity_field_validation for {field_name}")


@pytest.fixture(scope="module")
def entity_configs() -> dict[str, dict[str, Any]]:
    configs: dict[str, dict[str, Any]] = {}
    for path in sorted(ENTITY_CONFIG_ROOT.glob("*.yaml")):
        configs[path.stem] = _load_yaml(path)
    return configs


@pytest.fixture(scope="module")
def chembl_enums() -> dict[str, Any]:
    return _load_yaml(CHEMBL_ENUM_PATH)


@pytest.fixture(scope="module")
def matrix_rows() -> list[dict[str, str]]:
    return build_field_matrix_rows()


@pytest.mark.integration
def test_chembl_policy_registry_loader_matches_default_payload() -> None:
    loaded = ChemblPolicyRegistryLoader(CONFIGS_ROOT).load()

    assert loaded.strict_boolean_families == (
        DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.strict_boolean_families
    )
    assert loaded.strict_flag_families == (
        DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.strict_flag_families
    )
    assert loaded.controlled_vocabularies == (
        DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.controlled_vocabularies
    )
    assert loaded.ontology_families == (
        DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.ontology_families
    )
    assert loaded.publication_classification_fields == (
        DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.publication_classification_fields
    )
    assert loaded.reference_identifier_families == (
        DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.reference_identifier_families
    )


@pytest.mark.integration
def test_chembl_governed_fields_have_explicit_profile_classification(
    entity_configs: dict[str, dict[str, Any]],
    matrix_rows: list[dict[str, str]],
) -> None:
    expectations = _registry_governed_field_expectations()
    for field_ref, expectation in _config_enum_surface_expectations(
        entity_configs
    ).items():
        expectations.setdefault(field_ref, expectation)

    row_lookup = _matrix_row_lookup(matrix_rows)
    missing = sorted(
        field_ref for field_ref in expectations if field_ref not in row_lookup
    )
    assert not missing, (
        "Missing matrix classification rows for governed ChEMBL policy fields: "
        f"{missing}"
    )

    mismatches: list[str] = []
    for field_ref, (expected_classification, expected_source) in sorted(
        expectations.items()
    ):
        row = row_lookup[field_ref]
        actual_classification = _row_classification(row)
        if actual_classification not in ALLOWED_FIELD_CLASSIFICATIONS:
            mismatches.append(
                f"{field_ref}: unsupported classification {actual_classification!r}"
            )
        if actual_classification != expected_classification:
            mismatches.append(
                f"{field_ref}: expected classification {expected_classification!r}, "
                f"got {actual_classification!r}"
            )
        actual_source = _normalize_source_path(row["controlled_vocabulary_source"])
        if actual_source != _normalize_source_path(expected_source):
            mismatches.append(
                f"{field_ref}: expected source {expected_source!r}, got "
                f"{row['controlled_vocabulary_source']!r}"
            )

    assert not mismatches, "ChEMBL policy classification drift:\n" + "\n".join(
        mismatches
    )


@pytest.mark.integration
def test_all_current_chembl_profiles_participate_in_parity_suite(
    entity_configs: dict[str, dict[str, Any]],
    matrix_rows: list[dict[str, str]],
) -> None:
    registered_profiles = {
        entity
        for provider, entity in NORMALIZATION_PROFILE_REGISTRY
        if provider == "chembl"
    }
    matrix_profiles = {
        row["pipeline_name"].removeprefix("chembl_")
        for row in matrix_rows
        if row["pipeline_name"].startswith("chembl_")
    }

    missing_entity_configs = sorted(registered_profiles - set(entity_configs))
    missing_matrix_profiles = sorted(registered_profiles - matrix_profiles)

    assert not missing_entity_configs, (
        "ChEMBL parity suite is missing entity configs for registered profiles: "
        f"{missing_entity_configs}"
    )
    assert not missing_matrix_profiles, (
        "ChEMBL parity suite is missing matrix coverage for registered profiles: "
        f"{missing_matrix_profiles}"
    )


@pytest.mark.integration
def test_chembl_unit_policy_families_and_controlled_json_lists_keep_structural_parity(
    matrix_rows: list[dict[str, str]],
) -> None:
    row_lookup = _matrix_row_lookup(matrix_rows)
    ordering_policy = {
        f"{policy.pipeline_name}.{policy.field_name}": policy
        for policy in CHEMBL_JSON_ORDERING_POLICY
    }

    raw_unit_fields = next(
        family.fields
        for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.controlled_vocabularies
        if family.family_name == "raw_units"
    )
    for field_ref in sorted(raw_unit_fields):
        row = row_lookup[field_ref]
        assert _row_classification(row) == "unit-like"
        assert row["controlled_vocabulary_source"] == CHEMBL_CONTROLLED_VOCAB_CONFIG

    standard_unit_fields = next(
        family.fields
        for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.controlled_vocabularies
        if family.family_name == "standard_units"
    )
    for field_ref in sorted(standard_unit_fields):
        row = row_lookup[field_ref]
        assert _row_classification(row) == "strict enum"
        assert row["strictness"] == "strict_enum"
        assert row["dq_coverage"] == "enum:error"
        assert row["controlled_vocabulary_source"] == CHEMBL_CONTROLLED_VOCAB_CONFIG

    controlled_json_fields = {
        field_ref
        for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.controlled_vocabularies
        if family.invalid_value_mode == "reject_unknown_json_array_element"
        for field_ref in family.fields
    }
    for field_ref in sorted(controlled_json_fields):
        row = row_lookup[field_ref]
        assert _row_classification(row) == "controlled vocabulary"
        assert row["set_like"] == "true"
        assert ordering_policy[field_ref].order_semantics == "set_like"
        assert row["dq_coverage"] == "custom:error"


@pytest.mark.integration
def test_chembl_json_ordering_policy_is_not_redeclared_in_entity_hash_configs(
    entity_configs: dict[str, dict[str, Any]],
) -> None:
    regressions: list[str] = []

    for entity, config in sorted(entity_configs.items()):
        hash_policy = config.get("hash_policy")
        if not isinstance(hash_policy, dict):
            continue
        nested_policy = hash_policy.get("hash_policy")
        if not isinstance(nested_policy, dict):
            continue
        field_ordering = nested_policy.get("field_ordering")
        if isinstance(field_ordering, dict) and field_ordering:
            regressions.append(
                f"chembl_{entity}: unexpected hash_policy.hash_policy.field_ordering"
            )

    assert not regressions, (
        "ChEMBL JSON ordering policy must stay domain-authoritative only: "
        + "; ".join(regressions)
    )


@pytest.mark.integration
def test_chembl_json_ordering_policy_matches_runtime_profile_set_like_semantics() -> (
    None
):
    regressions: list[str] = []

    for policy in CHEMBL_JSON_ORDERING_POLICY:
        entity = policy.pipeline_name.removeprefix("chembl_")
        profile = NORMALIZATION_PROFILE_REGISTRY.get(("chembl", entity))
        if profile is None:
            regressions.append(
                f"{policy.pipeline_name}.{policy.field_name}: missing profile"
            )
            continue
        if policy.field_name not in profile.fields:
            regressions.append(
                f"{policy.pipeline_name}.{policy.field_name}: missing profile field"
            )
            continue
        is_set_like = policy.field_name in profile.set_like_fields
        if is_set_like != policy.is_set_like:
            regressions.append(
                f"{policy.pipeline_name}.{policy.field_name}: "
                f"policy_set_like={policy.is_set_like}, profile_set_like={is_set_like}"
            )

    assert not regressions, (
        "ChEMBL JSON ordering runtime profile semantics drifted:\n"
        + "\n".join(regressions)
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "pipeline_name",
    [
        "chembl_assay",
        "chembl_molecule",
        "chembl_publication",
        "chembl_target",
        "chembl_target_component",
    ],
)
def test_chembl_pipeline_loader_projects_empty_field_ordering_shim(
    pipeline_name: str,
) -> None:
    loaded = load_pipeline_config(pipeline_name)

    assert loaded.content_hash_policy is not None
    assert loaded.content_hash_policy.field_ordering == {}


@pytest.mark.integration
def test_confidence_description_registry_profile_and_dq_surfaces_are_aligned(
    entity_configs: dict[str, dict[str, Any]],
    chembl_enums: dict[str, Any],
    matrix_rows: list[dict[str, str]],
) -> None:
    row = _matrix_row_lookup(matrix_rows)["chembl_assay.confidence_description"]
    validation = _entity_field_validation(
        entity_configs["assay"],
        "confidence_description",
    )
    family = next(
        family
        for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.controlled_vocabularies
        if family.family_name == "assay_confidence_descriptions"
    )

    assert "chembl_assay.confidence_description" in family.fields
    assert family.invalid_value_mode == "reject_unknown_lexeme"
    assert _row_classification(row) == "strict enum"
    assert row["controlled_vocabulary_source"] == CHEMBL_CONTROLLED_VOCAB_CONFIG
    assert row["dq_coverage"] == "enum:error"
    assert row["strictness"] == "strict_enum"

    assert validation["type"] == "enum"
    assert validation["allowed"] == chembl_enums["assay"]["confidence_descriptions"]
    assert (
        CHEMBL_ASSAY_PROFILE.rule_for("confidence_description").normalizer(
            "mystery confidence"
        )
        is None
    )
