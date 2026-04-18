"""Canonical registry for shipped normalization profiles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeVar

from bioetl.domain.normalization.profiles.base import NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_activity import (
    CHEMBL_ACTIVITY_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_assay import (
    CHEMBL_ASSAY_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_assay_parameters import (
    CHEMBL_ASSAY_PARAMETERS_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_cell_line import (
    CHEMBL_CELL_LINE_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_compound_record import (
    CHEMBL_COMPOUND_RECORD_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_molecule import (
    CHEMBL_MOLECULE_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_protein_class import (
    CHEMBL_PROTEIN_CLASS_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_publication import (
    CHEMBL_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_publication_similarity import (
    CHEMBL_PUBLICATION_SIMILARITY_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_publication_term import (
    CHEMBL_PUBLICATION_TERM_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_subcellular_fraction import (
    CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_target import (
    CHEMBL_TARGET_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_target_component import (
    CHEMBL_TARGET_COMPONENT_PROFILE,
)
from bioetl.domain.normalization.profiles.chembl_tissue import (
    CHEMBL_TISSUE_PROFILE,
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


TValue = TypeVar("TValue")


@dataclass(frozen=True, slots=True)
class _NormalizationProfileDeclaration:
    """One shipped normalization-profile registry declaration."""

    provider: str
    entity_type: str
    profile: NormalizationProfile
    module_path: str


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


T = TypeVar("T")


def _resolve_normalization_profile_value(
    mapping: Mapping[tuple[str, str], TValue],
    provider: str,
    entity_type: str | None,
) -> TValue | None:
    """Resolve one canonical registry value by provider/entity coordinates."""
    coordinates = normalize_normalization_profile_coordinates(provider, entity_type)
    if coordinates is None:
        return None
    return mapping.get(coordinates)


_NORMALIZATION_PROFILE_DECLARATIONS: tuple[_NormalizationProfileDeclaration, ...] = (
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="activity",
        profile=CHEMBL_ACTIVITY_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_activity.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="assay",
        profile=CHEMBL_ASSAY_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_assay.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="assay_parameters",
        profile=CHEMBL_ASSAY_PARAMETERS_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="cell_line",
        profile=CHEMBL_CELL_LINE_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_cell_line.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="compound_record",
        profile=CHEMBL_COMPOUND_RECORD_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_compound_record.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="molecule",
        profile=CHEMBL_MOLECULE_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_molecule.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="protein_class",
        profile=CHEMBL_PROTEIN_CLASS_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_protein_class.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="publication",
        profile=CHEMBL_PUBLICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_publication.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="publication_similarity",
        profile=CHEMBL_PUBLICATION_SIMILARITY_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_publication_similarity.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="publication_term",
        profile=CHEMBL_PUBLICATION_TERM_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_publication_term.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="subcellular_fraction",
        profile=CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_subcellular_fraction.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="target",
        profile=CHEMBL_TARGET_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_target.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="target_component",
        profile=CHEMBL_TARGET_COMPONENT_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_target_component.py",
    ),
    _NormalizationProfileDeclaration(
        provider="chembl",
        entity_type="tissue",
        profile=CHEMBL_TISSUE_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/chembl_tissue.py",
    ),
    _NormalizationProfileDeclaration(
        provider="crossref",
        entity_type="publication",
        profile=CROSSREF_PUBLICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/crossref_publication.py",
    ),
    _NormalizationProfileDeclaration(
        provider="openalex",
        entity_type="publication",
        profile=OPENALEX_PUBLICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/openalex_publication.py",
    ),
    _NormalizationProfileDeclaration(
        provider="pubchem",
        entity_type="compound",
        profile=PUBCHEM_COMPOUND_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/pubchem_compound.py",
    ),
    _NormalizationProfileDeclaration(
        provider="pubmed",
        entity_type="publication",
        profile=PUBMED_PUBLICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/pubmed_publication.py",
    ),
    _NormalizationProfileDeclaration(
        provider="semanticscholar",
        entity_type="publication",
        profile=SEMANTICSCHOLAR_PUBLICATION_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/semanticscholar_publication.py",
    ),
    _NormalizationProfileDeclaration(
        provider="uniprot",
        entity_type="idmapping",
        profile=UNIPROT_IDMAPPING_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/uniprot_idmapping.py",
    ),
    _NormalizationProfileDeclaration(
        provider="uniprot",
        entity_type="protein",
        profile=UNIPROT_PROTEIN_PROFILE,
        module_path="src/bioetl/domain/normalization/profiles/uniprot_protein.py",
    ),
)


def build_normalization_profile_registry() -> Mapping[
    tuple[str, str], NormalizationProfile
]:
    """Return the immutable registry of shipped normalization profiles."""
    return {
        (declaration.provider, declaration.entity_type): declaration.profile
        for declaration in _NORMALIZATION_PROFILE_DECLARATIONS
    }


def build_normalization_profile_module_paths() -> Mapping[tuple[str, str], str]:
    """Return canonical source-module paths for shipped normalization profiles."""
    return {
        (declaration.provider, declaration.entity_type): declaration.module_path
        for declaration in _NORMALIZATION_PROFILE_DECLARATIONS
    }


NORMALIZATION_PROFILE_REGISTRY = build_normalization_profile_registry()
NORMALIZATION_PROFILE_MODULE_PATHS = build_normalization_profile_module_paths()


def resolve_normalization_profile(
    provider: str,
    entity_type: str | None,
) -> NormalizationProfile | None:
    """Resolve one shipped normalization profile by provider/entity."""
    return _resolve_normalization_profile_value(
        NORMALIZATION_PROFILE_REGISTRY,
        provider,
        entity_type,
    )


def resolve_normalization_profile_module_path(
    provider: str,
    entity_type: str | None,
) -> str | None:
    """Resolve one shipped normalization profile source-module path by provider/entity."""
    return _resolve_normalization_profile_value(
        NORMALIZATION_PROFILE_MODULE_PATHS,
        provider,
        entity_type,
    )
