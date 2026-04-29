"""Tests for shared ChEMBL controlled-vocabulary and ontology policy surfaces."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.domain.normalization.profiles._chembl_policy_registry import (
    CHEMBL_CONTROLLED_VOCAB_CONFIG,
    CHEMBL_ONTOLOGY_POLICY_CONFIG,
    DEFAULT_CHEMBL_POLICY_REGISTRY_DATA,
    PUBLICATION_CLASSIFICATION_CONFIG,
    ChemblControlledVocabularyFamily,
    ChemblOntologyPolicyFamily,
    ChemblPolicyRegistryData,
    ChemblStrictScalarFamily,
    chembl_boolean_family_fields,
    chembl_controlled_family_fields,
    chembl_flag_family_fields,
    chembl_ontology_family_fields,
    chembl_policy_surface,
    initialize_chembl_policy_registry,
)


def _load_yaml(path: str) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(autouse=True)
def reset_chembl_policy_registry() -> Iterator[None]:
    initialize_chembl_policy_registry(DEFAULT_CHEMBL_POLICY_REGISTRY_DATA)
    try:
        yield
    finally:
        initialize_chembl_policy_registry(DEFAULT_CHEMBL_POLICY_REGISTRY_DATA)


def test_chembl_policy_surface_points_to_externalized_registry_sources() -> None:
    units = chembl_policy_surface("activity", "units")
    is_oa = chembl_policy_surface("publication", "is_oa")
    standard_flag = chembl_policy_surface("activity", "standard_flag")
    bao_format = chembl_policy_surface("activity", "bao_format")
    bao_endpoint_iri = chembl_policy_surface("activity", "bao_endpoint_iri")
    assay_bao_mapping_status = chembl_policy_surface(
        "assay",
        "bao_format_mapping_status",
    )
    bao_version = chembl_policy_surface("activity", "bao_ontology_version")
    publication_class = chembl_policy_surface("publication", "publication_class")

    assert units is not None
    assert units.category == "controlled_vocabulary"
    assert units.registry_source == CHEMBL_CONTROLLED_VOCAB_CONFIG

    assert is_oa is not None
    assert is_oa.category == "strict_boolean"
    assert is_oa.registry_source == CHEMBL_CONTROLLED_VOCAB_CONFIG

    assert standard_flag is not None
    assert standard_flag.category == "strict_flag"
    assert standard_flag.registry_source == CHEMBL_CONTROLLED_VOCAB_CONFIG

    assert bao_format is not None
    assert bao_format.category == "ontology_reference_identifier"
    assert bao_format.registry_source == CHEMBL_ONTOLOGY_POLICY_CONFIG

    assert bao_endpoint_iri is not None
    assert bao_endpoint_iri.category == "ontology_reference_identifier"
    assert bao_endpoint_iri.registry_source == CHEMBL_ONTOLOGY_POLICY_CONFIG

    assert assay_bao_mapping_status is not None
    assert assay_bao_mapping_status.category == "ontology_reference_metadata"
    assert assay_bao_mapping_status.registry_source == CHEMBL_ONTOLOGY_POLICY_CONFIG

    assert bao_version is not None
    assert bao_version.category == "ontology_reference_metadata"
    assert bao_version.registry_source == CHEMBL_ONTOLOGY_POLICY_CONFIG

    assert publication_class is not None
    assert publication_class.category == "derived_vocabulary"
    assert publication_class.registry_source == PUBLICATION_CLASSIFICATION_CONFIG


def test_chembl_policy_registry_configs_cover_declared_policy_fields() -> None:
    controlled = _load_yaml(CHEMBL_CONTROLLED_VOCAB_CONFIG)
    ontology = _load_yaml(CHEMBL_ONTOLOGY_POLICY_CONFIG)

    controlled_fields = {
        field
        for policy in controlled["controlled_vocabularies"].values()
        for field in policy["fields"]
    }
    strict_boolean_fields = {
        field
        for policy in controlled["strict_boolean_families"].values()
        for field in policy["fields"]
    }
    strict_flag_fields = {
        field
        for policy in controlled["strict_flag_families"].values()
        for field in policy["fields"]
    }
    ontology_fields = {
        field for policy in ontology["families"].values() for field in policy["fields"]
    }
    ontology_companion_fields = {
        field
        for policy in ontology["families"].values()
        for companion_fields in policy.get("companion_fields", {}).values()
        for field in companion_fields
    }

    assert "chembl_activity.units" in controlled_fields
    assert "chembl_assay_parameters.type" in controlled_fields
    assert "chembl_publication.is_oa" in strict_boolean_fields
    assert "chembl_activity.standard_flag" in strict_flag_fields
    assert "chembl_molecule.inorganic_flag" in strict_flag_fields
    assert "chembl_activity.bao_format" in ontology_fields
    assert "chembl_cell_line.cellosaurus_id" in ontology_fields
    assert "chembl_cell_line.clo_id" in ontology_fields
    assert "chembl_assay.bao_format_mapping_status" in ontology_companion_fields
    assert "chembl_tissue.bto_iri" in ontology_companion_fields
    assert "chembl_cell_line.clo_ontology_version" in ontology_companion_fields


def test_chembl_policy_registry_exposes_profile_authoring_field_sets() -> None:
    assert chembl_boolean_family_fields("bool_like", entity="publication") == (
        frozenset({"is_oa"})
    )
    assert chembl_flag_family_fields("binary_flags", entity="activity") == frozenset(
        {"standard_flag", "potential_duplicate", "manual_curation_flag"}
    )
    assert chembl_controlled_family_fields("units", entity="activity") == frozenset(
        {"units", "standard_units", "qudt_units"}
    )
    assert chembl_controlled_family_fields(
        "units", entity="assay_parameters"
    ) == frozenset({"units", "standard_units"})
    assert chembl_flag_family_fields(
        "provider_code_flags",
        entity="molecule",
    ) == frozenset({"first_in_class", "inorganic_flag", "natural_product", "prodrug"})
    assert chembl_controlled_family_fields(
        "operators", entity="assay_parameters"
    ) == frozenset({"relation"})
    assert chembl_ontology_family_fields("bao", entity="activity") == frozenset(
        {"bao_endpoint", "bao_format"}
    )
    assert chembl_ontology_family_fields("clo", entity="cell_line") == frozenset(
        {"clo_id"}
    )


def test_chembl_policy_surface_returns_none_for_ungoverned_free_text_fields() -> None:
    assert chembl_policy_surface("target", "organism") is None


def test_chembl_policy_registry_can_be_reinitialized_from_in_memory_data() -> None:
    initialize_chembl_policy_registry(
        ChemblPolicyRegistryData(
            strict_boolean_families=(
                ChemblStrictScalarFamily(
                    family_name="mini_boolean",
                    invalid_value_mode="coerce_common_boolean_lexemes",
                    fields=("chembl_publication.is_oa",),
                ),
            ),
            strict_flag_families=(
                ChemblStrictScalarFamily(
                    family_name="mini_flag",
                    invalid_value_mode="coerce_common_flag_lexemes",
                    fields=("chembl_activity.standard_flag",),
                ),
            ),
            controlled_vocabularies=(
                ChemblControlledVocabularyFamily(
                    family_name="mini_units",
                    invalid_value_mode="preserve_unknown_lexeme",
                    fields=("chembl_activity.units",),
                ),
            ),
            ontology_families=(
                ChemblOntologyPolicyFamily(
                    family_name="mini_ontology",
                    fields=("chembl_cell_line.cellosaurus_id",),
                    code_label_fields=("chembl_assay.bao_label",),
                    iri_fields=("chembl_activity.bao_endpoint_iri",),
                    mapping_status_fields=(
                        "chembl_activity.bao_endpoint_mapping_status",
                    ),
                    version_fields=("chembl_activity.bao_ontology_version",),
                ),
            ),
            publication_classification_fields=("publication_class",),
        )
    )

    assert chembl_controlled_family_fields("mini_units", entity="activity") == (
        frozenset({"units"})
    )
    assert chembl_boolean_family_fields("mini_boolean", entity="publication") == (
        frozenset({"is_oa"})
    )
    assert chembl_flag_family_fields("mini_flag", entity="activity") == frozenset(
        {"standard_flag"}
    )
    assert chembl_ontology_family_fields(
        "mini_ontology",
        entity="assay",
        include_code_label_fields=True,
    ) == frozenset({"bao_label"})
    iri_surface = chembl_policy_surface("activity", "bao_endpoint_iri")
    assert iri_surface is not None
    assert iri_surface.category == "ontology_reference_identifier"
    status_surface = chembl_policy_surface("activity", "bao_endpoint_mapping_status")
    assert status_surface is not None
    assert status_surface.category == "ontology_reference_metadata"
    publication_class = chembl_policy_surface("publication", "publication_class")
    assert publication_class is not None
    assert publication_class.registry_source == PUBLICATION_CLASSIFICATION_CONFIG
    assert chembl_policy_surface("activity", "relation") is None
