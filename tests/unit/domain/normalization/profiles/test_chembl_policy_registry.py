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
"""Tests for shared ChEMBL policy registry surfaces."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.domain.normalization.profiles.chembl_policy_registry import (
    CHEMBL_CONTROLLED_VOCAB_CONFIG,
    CHEMBL_ONTOLOGY_POLICY_CONFIG,
    CHEMBL_REFERENCE_IDENTIFIER_CONFIG,
    DEFAULT_CHEMBL_POLICY_REGISTRY_DATA,
    PUBLICATION_CLASSIFICATION_CONFIG,
    ChemblControlledVocabularyFamily,
    ChemblOntologyPolicyFamily,
    ChemblPolicyRegistryData,
    ChemblReferenceIdentifierFamily,
    ChemblStrictScalarFamily,
    chembl_boolean_family_fields,
    chembl_controlled_family_fields,
    chembl_flag_family_fields,
    chembl_ontology_family_fields,
    chembl_policy_surface,
    chembl_reference_identifier_family_fields,
    initialize_chembl_policy_registry,
)


pytestmark = pytest.mark.unit


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
    action_type = chembl_policy_surface("activity", "action_type")
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
    publication_doi = chembl_policy_surface("publication", "doi")
    publication_mesh_id = chembl_policy_surface("publication_term", "mesh_id")
    target_taxonomy_id = chembl_policy_surface("target", "taxonomy_id")

    assert action_type is not None
    assert action_type.category == "controlled_vocabulary"
    assert action_type.registry_source == CHEMBL_CONTROLLED_VOCAB_CONFIG
    assert action_type.invalid_value_mode == "preserve_unknown_uppercase_lexeme"

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

    assert publication_doi is not None
    assert publication_doi.category == "reference_identifier"
    assert publication_doi.registry_source == CHEMBL_REFERENCE_IDENTIFIER_CONFIG

    assert publication_mesh_id is not None
    assert publication_mesh_id.category == "reference_identifier"
    assert publication_mesh_id.registry_source == CHEMBL_REFERENCE_IDENTIFIER_CONFIG

    assert target_taxonomy_id is not None
    assert target_taxonomy_id.category == "reference_identifier"
    assert target_taxonomy_id.registry_source == CHEMBL_REFERENCE_IDENTIFIER_CONFIG


def test_chembl_policy_registry_configs_cover_declared_policy_fields() -> None:
    controlled = _load_yaml(CHEMBL_CONTROLLED_VOCAB_CONFIG)
    ontology = _load_yaml(CHEMBL_ONTOLOGY_POLICY_CONFIG)
    reference_identifiers = _load_yaml(CHEMBL_REFERENCE_IDENTIFIER_CONFIG)

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
    reference_identifier_fields = {
        field
        for policy in reference_identifiers["reference_identifier_families"].values()
        for field in policy["fields"]
    }

    assert "chembl_activity.units" in controlled_fields
    assert "chembl_activity.action_type" in controlled_fields
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
    assert "chembl_target.taxonomy_id" in reference_identifier_fields
    assert "chembl_publication.doi" in reference_identifier_fields
    assert "chembl_publication_term.mesh_id" in reference_identifier_fields
    assert "chembl_target.component_accessions" in reference_identifier_fields
    assert (
        ontology["families"]["caloha"]["companion_governance"]
        == "identifier_only_no_companion_bundle"
    )
    assert (
        ontology["families"]["cellosaurus"]["companion_governance"]
        == "identifier_only_no_companion_bundle"
    )


def test_chembl_policy_registry_exposes_profile_authoring_field_sets() -> None:
    assert chembl_boolean_family_fields("bool_like", entity="publication") == (
        frozenset({"is_oa"})
    )
    assert chembl_flag_family_fields("binary_flags", entity="activity") == frozenset(
        {"standard_flag", "potential_duplicate", "manual_curation_flag"}
    )
    assert chembl_controlled_family_fields("raw_units", entity="activity") == frozenset(
        {"units"}
    )
    assert chembl_controlled_family_fields(
        "activity_action_types",
        entity="activity",
    ) == frozenset({"action_type"})
    assert chembl_controlled_family_fields(
        "standard_units", entity="activity"
    ) == frozenset({"standard_units"})
    assert chembl_controlled_family_fields(
        "raw_units", entity="assay_parameters"
    ) == frozenset({"units"})
    assert chembl_controlled_family_fields(
        "standard_units", entity="assay_parameters"
    ) == frozenset({"standard_units"})
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
    assert chembl_ontology_family_fields("qudt", entity="activity") == frozenset(
        {"qudt_units"}
    )
    assert chembl_ontology_family_fields("clo", entity="cell_line") == frozenset(
        {"clo_id"}
    )
    assert chembl_reference_identifier_family_fields(
        "chembl",
        entity="assay",
    ) == frozenset({"assay_id", "cell_id", "publication_id", "target_id", "tissue_id"})
    assert chembl_reference_identifier_family_fields(
        "ncbi_taxonomy",
        entity="target",
    ) == frozenset({"taxonomy_id"})
    assert chembl_reference_identifier_family_fields(
        "uniprot_accession",
        entity="target",
    ) == frozenset({"component_accessions"})
    assert chembl_reference_identifier_family_fields(
        "doi",
        entity="publication",
    ) == frozenset({"doi", "publication_doi"})
    assert chembl_reference_identifier_family_fields(
        "pmid",
        entity="publication",
    ) == frozenset({"pmid", "publication_pmid"})
    assert chembl_reference_identifier_family_fields(
        "pmcid",
        entity="publication",
    ) == frozenset({"pmc_id", "publication_pmc_id"})
    assert chembl_reference_identifier_family_fields(
        "mesh",
        entity="publication_term",
    ) == frozenset({"mesh_id"})


def test_chembl_policy_surface_returns_none_for_ungoverned_free_text_fields() -> None:
    assert chembl_policy_surface("target", "organism") is None


def test_chembl_policy_registry_encodes_explicit_identifier_only_companion_governance() -> (
    None
):
    caloha = next(
        family
        for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.ontology_families
        if family.family_name == "caloha"
    )
    cellosaurus = next(
        family
        for family in DEFAULT_CHEMBL_POLICY_REGISTRY_DATA.ontology_families
        if family.family_name == "cellosaurus"
    )

    assert caloha.companion_governance == "identifier_only_no_companion_bundle"
    assert caloha.iri_fields == ()
    assert caloha.mapping_status_fields == ()
    assert caloha.version_fields == ()
    assert cellosaurus.companion_governance == "identifier_only_no_companion_bundle"
    assert cellosaurus.iri_fields == ()
    assert cellosaurus.mapping_status_fields == ()
    assert cellosaurus.version_fields == ()


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
            reference_identifier_families=(
                ChemblReferenceIdentifierFamily(
                    family_name="mini_reference",
                    reference_family="doi",
                    invalid_value_mode="canonicalize_or_null_blank",
                    fields=("chembl_publication.doi",),
                ),
            ),
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
    doi_surface = chembl_policy_surface("publication", "doi")
    assert doi_surface is not None
    assert doi_surface.category == "reference_identifier"
    assert doi_surface.registry_source == CHEMBL_REFERENCE_IDENTIFIER_CONFIG
    assert chembl_reference_identifier_family_fields(
        "mini_reference",
        entity="publication",
    ) == frozenset({"doi"})
    assert chembl_policy_surface("activity", "relation") is None
