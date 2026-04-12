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


def _resolve_normalization_profile_value[T](
    mapping: Mapping[tuple[str, str], T],
    provider: str,
    entity_type: str | None,
) -> T | None:
    """Resolve one canonical registry value by provider/entity coordinates."""
    coordinates = normalize_normalization_profile_coordinates(provider, entity_type)
    if coordinates is None:
        return None
    return mapping.get(coordinates)


def build_normalization_profile_registry() -> Mapping[tuple[str, str], NormalizationProfile]:
    """Return the immutable registry of shipped normalization profiles."""
    return {
        ("chembl", "activity"): CHEMBL_ACTIVITY_PROFILE,
        ("chembl", "assay"): CHEMBL_ASSAY_PROFILE,
        ("chembl", "assay_parameters"): CHEMBL_ASSAY_PARAMETERS_PROFILE,
        ("chembl", "cell_line"): CHEMBL_CELL_LINE_PROFILE,
        ("chembl", "compound_record"): CHEMBL_COMPOUND_RECORD_PROFILE,
        ("chembl", "molecule"): CHEMBL_MOLECULE_PROFILE,
        ("chembl", "protein_class"): CHEMBL_PROTEIN_CLASS_PROFILE,
        ("chembl", "publication"): CHEMBL_PUBLICATION_PROFILE,
        ("chembl", "publication_similarity"): CHEMBL_PUBLICATION_SIMILARITY_PROFILE,
        ("chembl", "publication_term"): CHEMBL_PUBLICATION_TERM_PROFILE,
        ("chembl", "subcellular_fraction"): CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
        ("chembl", "target"): CHEMBL_TARGET_PROFILE,
        ("chembl", "target_component"): CHEMBL_TARGET_COMPONENT_PROFILE,
        ("chembl", "tissue"): CHEMBL_TISSUE_PROFILE,
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
        (
            "chembl",
            "assay_parameters",
        ): "src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py",
        ("chembl", "cell_line"): "src/bioetl/domain/normalization/profiles/chembl_cell_line.py",
        (
            "chembl",
            "compound_record",
        ): "src/bioetl/domain/normalization/profiles/chembl_compound_record.py",
        ("chembl", "molecule"): "src/bioetl/domain/normalization/profiles/chembl_molecule.py",
        (
            "chembl",
            "protein_class",
        ): "src/bioetl/domain/normalization/profiles/chembl_protein_class.py",
        ("chembl", "publication"): "src/bioetl/domain/normalization/profiles/chembl_publication.py",
        (
            "chembl",
            "publication_similarity",
        ): "src/bioetl/domain/normalization/profiles/chembl_publication_similarity.py",
        (
            "chembl",
            "publication_term",
        ): "src/bioetl/domain/normalization/profiles/chembl_publication_term.py",
        (
            "chembl",
            "subcellular_fraction",
        ): "src/bioetl/domain/normalization/profiles/chembl_subcellular_fraction.py",
        ("chembl", "target"): "src/bioetl/domain/normalization/profiles/chembl_target.py",
        (
            "chembl",
            "target_component",
        ): "src/bioetl/domain/normalization/profiles/chembl_target_component.py",
        ("chembl", "tissue"): "src/bioetl/domain/normalization/profiles/chembl_tissue.py",
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
