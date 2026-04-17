"""Tests for canonical normalization profile registry helpers."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ASSAY_PROFILE,
    CHEMBL_MOLECULE_PROFILE,
    CHEMBL_PUBLICATION_PROFILE,
    CHEMBL_TARGET_PROFILE,
    CROSSREF_PUBLICATION_PROFILE,
    OPENALEX_PUBLICATION_PROFILE,
    PUBCHEM_COMPOUND_PROFILE,
    PUBMED_PUBLICATION_PROFILE,
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
    UNIPROT_IDMAPPING_PROFILE,
    UNIPROT_PROTEIN_PROFILE,
)
from bioetl.domain.normalization.profiles.registry import (
    NORMALIZATION_PROFILE_MODULE_PATHS,
    NORMALIZATION_PROFILE_REGISTRY,
    build_normalization_profile_module_paths,
    build_normalization_profile_registry,
    normalize_normalization_profile_coordinates,
    resolve_normalization_profile,
    resolve_normalization_profile_module_path,
)


def test_registry_contains_canonical_chembl_activity_profile() -> None:
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("chembl", "activity")]
        is CHEMBL_ACTIVITY_PROFILE
    )
    assert NORMALIZATION_PROFILE_REGISTRY[("chembl", "assay")] is CHEMBL_ASSAY_PROFILE
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("chembl", "molecule")]
        is CHEMBL_MOLECULE_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("chembl", "publication")]
        is CHEMBL_PUBLICATION_PROFILE
    )
    assert NORMALIZATION_PROFILE_REGISTRY[("chembl", "target")] is CHEMBL_TARGET_PROFILE
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("crossref", "publication")]
        is CROSSREF_PUBLICATION_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("openalex", "publication")]
        is OPENALEX_PUBLICATION_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("pubmed", "publication")]
        is PUBMED_PUBLICATION_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("pubchem", "compound")]
        is PUBCHEM_COMPOUND_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("semanticscholar", "publication")]
        is SEMANTICSCHOLAR_PUBLICATION_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("uniprot", "idmapping")]
        is UNIPROT_IDMAPPING_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("uniprot", "protein")]
        is UNIPROT_PROTEIN_PROFILE
    )


def test_build_registry_matches_exported_registry() -> None:
    assert build_normalization_profile_registry() == NORMALIZATION_PROFILE_REGISTRY


def test_build_module_paths_match_exported_mapping() -> None:
    assert (
        build_normalization_profile_module_paths() == NORMALIZATION_PROFILE_MODULE_PATHS
    )


def test_profile_registry_and_module_paths_share_same_coordinates() -> None:
    assert set(NORMALIZATION_PROFILE_REGISTRY) == set(
        NORMALIZATION_PROFILE_MODULE_PATHS
    )


def test_registry_exports_canonical_profile_module_paths() -> None:
    assert (
        NORMALIZATION_PROFILE_MODULE_PATHS[("chembl", "activity")]
        == "src/bioetl/domain/normalization/profiles/chembl_activity.py"
    )
    assert (
        NORMALIZATION_PROFILE_MODULE_PATHS[("crossref", "publication")]
        == "src/bioetl/domain/normalization/profiles/crossref_publication.py"
    )
    assert (
        NORMALIZATION_PROFILE_MODULE_PATHS[("uniprot", "protein")]
        == "src/bioetl/domain/normalization/profiles/uniprot_protein.py"
    )


def test_registry_contains_additional_publication_and_compound_profiles() -> None:
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("crossref", "publication")]
        is CROSSREF_PUBLICATION_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("openalex", "publication")]
        is OPENALEX_PUBLICATION_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("pubmed", "publication")]
        is PUBMED_PUBLICATION_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("semanticscholar", "publication")]
        is SEMANTICSCHOLAR_PUBLICATION_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("pubchem", "compound")]
        is PUBCHEM_COMPOUND_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("chembl", "molecule")]
        is CHEMBL_MOLECULE_PROFILE
    )
    assert (
        NORMALIZATION_PROFILE_REGISTRY[("uniprot", "protein")]
        is UNIPROT_PROTEIN_PROFILE
    )


def test_normalize_coordinates_trims_and_lowercases() -> None:
    assert normalize_normalization_profile_coordinates(" ChEMBL ", " Activity ") == (
        "chembl",
        "activity",
    )


def test_normalize_coordinates_rejects_blank_entity() -> None:
    assert normalize_normalization_profile_coordinates("chembl", "   ") is None


def test_resolve_profile_uses_registry_coordinates() -> None:
    assert (
        resolve_normalization_profile(" ChEMBL ", " Activity ")
        is CHEMBL_ACTIVITY_PROFILE
    )
    assert resolve_normalization_profile(" ChEMBL ", " Assay ") is CHEMBL_ASSAY_PROFILE
    assert (
        resolve_normalization_profile(" ChEMBL ", " Molecule ")
        is CHEMBL_MOLECULE_PROFILE
    )
    assert (
        resolve_normalization_profile(" ChEMBL ", " Publication ")
        is CHEMBL_PUBLICATION_PROFILE
    )
    assert (
        resolve_normalization_profile(" ChEMBL ", " Target ") is CHEMBL_TARGET_PROFILE
    )
    assert (
        resolve_normalization_profile(" CrossRef ", " Publication ")
        is CROSSREF_PUBLICATION_PROFILE
    )
    assert (
        resolve_normalization_profile(" OpenAlex ", " Publication ")
        is OPENALEX_PUBLICATION_PROFILE
    )
    assert (
        resolve_normalization_profile(" SemanticScholar ", " Publication ")
        is SEMANTICSCHOLAR_PUBLICATION_PROFILE
    )
    assert (
        resolve_normalization_profile(" UniProt ", " IdMapping ")
        is UNIPROT_IDMAPPING_PROFILE
    )
    assert (
        resolve_normalization_profile(" UniProt ", " Protein ")
        is UNIPROT_PROTEIN_PROFILE
    )
    assert resolve_normalization_profile("chembl", None) is None


def test_resolve_profile_module_path_uses_registry_coordinates() -> None:
    assert (
        resolve_normalization_profile_module_path(" ChEMBL ", " Activity ")
        == "src/bioetl/domain/normalization/profiles/chembl_activity.py"
    )
    assert (
        resolve_normalization_profile_module_path(" SemanticScholar ", " Publication ")
        == "src/bioetl/domain/normalization/profiles/semanticscholar_publication.py"
    )
    assert resolve_normalization_profile_module_path("chembl", None) is None


def test_profile_and_module_path_resolution_share_coordinate_normalization() -> None:
    provider = " ChEMBL "
    entity_type = " Molecule "

    assert (
        resolve_normalization_profile(provider, entity_type) is CHEMBL_MOLECULE_PROFILE
    )
    assert (
        resolve_normalization_profile_module_path(provider, entity_type)
        == "src/bioetl/domain/normalization/profiles/chembl_molecule.py"
    )
