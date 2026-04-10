"""Canonical registry for shipped normalization profiles."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.normalization.profiles.base import NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_activity import (
    CHEMBL_ACTIVITY_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_assay import (
    CHEMBL_ASSAY_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_molecule import (
    CHEMBL_MOLECULE_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_publication import (
    CHEMBL_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_target import (
    CHEMBL_TARGET_PROFILE,
)
from bioetl.domain.normalization.profiles.crossref_publication import (
    CROSSREF_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.openalex_publication import (
    OPENALEX_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.pubchem_compound import (
    PUBCHEM_COMPOUND_PROFILE,
)
from bioetl.domain.normalization.profiles.pubmed_publication import (
    PUBMED_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.semanticscholar_publication import (
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.uniprot_idmapping import (
    UNIPROT_IDMAPPING_PROFILE,
)
from bioetl.domain.normalization.profiles.uniprot_protein import (
    UNIPROT_PROTEIN_PROFILE,
)

__all__ = [
    "NORMALIZATION_PROFILE_MODULE_PATHS",
    "NORMALIZATION_PROFILE_REGISTRY",
    "build_normalization_profile_module_paths",
    "build_normalization_profile_registry",
    "normalize_normalization_profile_coordinates",
    "resolve_normalization_profile",
    "resolve_normalization_profile_module_path",
]


def normalize_normalization_profile_coordinates(
    provider: str,
    entity_type: str | None,
) -> tuple[str, str] | None:
    """Return canonical provider/entity coordinates for profile lookup."""
    normalized_provider = provider.strip().lower()
    normalized_entity = None if entity_type is None else entity_type.strip().lower()
    if not normalized_provider or normalized_entity is None or not normalized_entity:
        return None
    return normalized_provider, normalized_entity


def build_normalization_profile_registry() -> Mapping[tuple[str, str], NormalizationProfile]:
    """Return the immutable registry of shipped normalization profiles."""
    return {
        ("chembl", "activity"): CHEMBL_ACTIVITY_PROFILE,
        ("chembl", "assay"): CHEMBL_ASSAY_PROFILE,
        ("chembl", "molecule"): CHEMBL_MOLECULE_PROFILE,
        ("chembl", "publication"): CHEMBL_PUBLICATION_PROFILE,
        ("chembl", "target"): CHEMBL_TARGET_PROFILE,
        ("crossref", "publication"): CROSSREF_PUBLICATION_PROFILE,
        ("openalex", "publication"): OPENALEX_PUBLICATION_PROFILE,
        ("pubchem", "compound"): PUBCHEM_COMPOUND_PROFILE,
        ("pubmed", "publication"): PUBMED_PUBLICATION_PROFILE,
        ("semanticscholar", "publication"): SEMANTICSCHOLAR_PUBLICATION_PROFILE,
        ("uniprot", "idmapping"): UNIPROT_IDMAPPING_PROFILE,
        ("uniprot", "protein"): UNIPROT_PROTEIN_PROFILE,
    }


def build_normalization_profile_module_paths() -> Mapping[tuple[str, str], str]:
    """Return canonical source-module paths for shipped normalization profiles."""
    return {
        ("chembl", "activity"): "src/bioetl/domain/normalization/profiles/chembl_activity.py",
        ("chembl", "assay"): "src/bioetl/domain/normalization/profiles/chembl_assay.py",
        ("chembl", "molecule"): "src/bioetl/domain/normalization/profiles/chembl_molecule.py",
        ("chembl", "publication"): "src/bioetl/domain/normalization/profiles/chembl_publication.py",
        ("chembl", "target"): "src/bioetl/domain/normalization/profiles/chembl_target.py",
        (
            "crossref",
            "publication",
        ): "src/bioetl/domain/normalization/profiles/crossref_publication.py",
        (
            "openalex",
            "publication",
        ): "src/bioetl/domain/normalization/profiles/openalex_publication.py",
        ("pubchem", "compound"): "src/bioetl/domain/normalization/profiles/pubchem_compound.py",
        ("pubmed", "publication"): "src/bioetl/domain/normalization/profiles/pubmed_publication.py",
        (
            "semanticscholar",
            "publication",
        ): "src/bioetl/domain/normalization/profiles/semanticscholar_publication.py",
        ("uniprot", "idmapping"): "src/bioetl/domain/normalization/profiles/uniprot_idmapping.py",
        ("uniprot", "protein"): "src/bioetl/domain/normalization/profiles/uniprot_protein.py",
    }


NORMALIZATION_PROFILE_REGISTRY = build_normalization_profile_registry()
NORMALIZATION_PROFILE_MODULE_PATHS = build_normalization_profile_module_paths()


def resolve_normalization_profile(
    provider: str,
    entity_type: str | None,
) -> NormalizationProfile | None:
    """Resolve one shipped normalization profile by provider/entity."""
    coordinates = normalize_normalization_profile_coordinates(provider, entity_type)
    if coordinates is None:
        return None
    return NORMALIZATION_PROFILE_REGISTRY.get(coordinates)


def resolve_normalization_profile_module_path(
    provider: str,
    entity_type: str | None,
) -> str | None:
    """Resolve one shipped normalization profile source-module path by provider/entity."""
    coordinates = normalize_normalization_profile_coordinates(provider, entity_type)
    if coordinates is None:
        return None
    return NORMALIZATION_PROFILE_MODULE_PATHS.get(coordinates)
