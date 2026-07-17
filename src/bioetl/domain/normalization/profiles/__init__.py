"""Provider/entity normalization profiles.

This facade preserves ``from bioetl.domain.normalization.profiles import X``
imports without eagerly importing every shipped normalization profile.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.normalization.profiles.base import (
        FieldRule as FieldRule,
    )
    from bioetl.domain.normalization.profiles.base import (
        FieldRuleIdentity as FieldRuleIdentity,
    )
    from bioetl.domain.normalization.profiles.base import (
        NormalizationProfile as NormalizationProfile,
    )
    from bioetl.domain.normalization.profiles.base import (
        NormalizationProfileIdentity as NormalizationProfileIdentity,
    )
    from bioetl.domain.normalization.profiles.chembl_activity import (
        CHEMBL_ACTIVITY_PROFILE as CHEMBL_ACTIVITY_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_activity import (
        CHEMBL_ACTIVITY_SCHEMA_FIELDS as CHEMBL_ACTIVITY_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_assay import (
        CHEMBL_ASSAY_PROFILE as CHEMBL_ASSAY_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_assay import (
        CHEMBL_ASSAY_SCHEMA_FIELDS as CHEMBL_ASSAY_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_assay_parameters import (
        CHEMBL_ASSAY_PARAMETERS_PROFILE as CHEMBL_ASSAY_PARAMETERS_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_assay_parameters import (
        CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS as CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_cell_line import (
        CHEMBL_CELL_LINE_PROFILE as CHEMBL_CELL_LINE_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_cell_line import (
        CHEMBL_CELL_LINE_SCHEMA_FIELDS as CHEMBL_CELL_LINE_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_compound_record import (
        CHEMBL_COMPOUND_RECORD_PROFILE as CHEMBL_COMPOUND_RECORD_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_compound_record import (
        CHEMBL_COMPOUND_RECORD_SCHEMA_FIELDS as CHEMBL_COMPOUND_RECORD_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_molecule import (
        CHEMBL_MOLECULE_PROFILE as CHEMBL_MOLECULE_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_molecule import (
        CHEMBL_MOLECULE_SCHEMA_FIELDS as CHEMBL_MOLECULE_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_protein_class import (
        CHEMBL_PROTEIN_CLASS_PROFILE as CHEMBL_PROTEIN_CLASS_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_protein_class import (
        CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS as CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_publication import (
        CHEMBL_PUBLICATION_PROFILE as CHEMBL_PUBLICATION_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_publication import (
        CHEMBL_PUBLICATION_SCHEMA_FIELDS as CHEMBL_PUBLICATION_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_publication_similarity import (
        CHEMBL_PUBLICATION_SIMILARITY_PROFILE as CHEMBL_PUBLICATION_SIMILARITY_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_publication_similarity import (
        CHEMBL_PUBLICATION_SIMILARITY_SCHEMA_FIELDS as CHEMBL_PUBLICATION_SIMILARITY_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_publication_term import (
        CHEMBL_PUBLICATION_TERM_PROFILE as CHEMBL_PUBLICATION_TERM_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_publication_term import (
        CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS as CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_subcellular_fraction import (
        CHEMBL_SUBCELLULAR_FRACTION_PROFILE as CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_subcellular_fraction import (
        CHEMBL_SUBCELLULAR_FRACTION_SCHEMA_FIELDS as CHEMBL_SUBCELLULAR_FRACTION_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_target import (
        CHEMBL_TARGET_PROFILE as CHEMBL_TARGET_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_target import (
        CHEMBL_TARGET_SCHEMA_FIELDS as CHEMBL_TARGET_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_target_component import (
        CHEMBL_TARGET_COMPONENT_PROFILE as CHEMBL_TARGET_COMPONENT_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_target_component import (
        CHEMBL_TARGET_COMPONENT_SCHEMA_FIELDS as CHEMBL_TARGET_COMPONENT_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_target_protein_classification import (
        CHEMBL_TARGET_PROTEIN_CLASSIFICATION_PROFILE as CHEMBL_TARGET_PROTEIN_CLASSIFICATION_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_target_protein_classification import (
        CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA_FIELDS as CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.chembl_tissue import (
        CHEMBL_TISSUE_PROFILE as CHEMBL_TISSUE_PROFILE,
    )
    from bioetl.domain.normalization.profiles.chembl_tissue import (
        CHEMBL_TISSUE_SCHEMA_FIELDS as CHEMBL_TISSUE_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.crossref_publication import (
        CROSSREF_PUBLICATION_PROFILE as CROSSREF_PUBLICATION_PROFILE,
    )
    from bioetl.domain.normalization.profiles.crossref_publication import (
        CROSSREF_PUBLICATION_SCHEMA_FIELDS as CROSSREF_PUBLICATION_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.openalex_publication import (
        OPENALEX_PUBLICATION_PROFILE as OPENALEX_PUBLICATION_PROFILE,
    )
    from bioetl.domain.normalization.profiles.openalex_publication import (
        OPENALEX_PUBLICATION_SCHEMA_FIELDS as OPENALEX_PUBLICATION_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.pubchem_compound import (
        PUBCHEM_COMPOUND_PROFILE as PUBCHEM_COMPOUND_PROFILE,
    )
    from bioetl.domain.normalization.profiles.pubchem_compound import (
        PUBCHEM_COMPOUND_SCHEMA_FIELDS as PUBCHEM_COMPOUND_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.pubmed_publication import (
        PUBMED_PUBLICATION_PROFILE as PUBMED_PUBLICATION_PROFILE,
    )
    from bioetl.domain.normalization.profiles.pubmed_publication import (
        PUBMED_PUBLICATION_SCHEMA_FIELDS as PUBMED_PUBLICATION_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.registry import (
        NORMALIZATION_PROFILE_REGISTRY as NORMALIZATION_PROFILE_REGISTRY,
    )
    from bioetl.domain.normalization.profiles.registry import (
        build_normalization_profile_registry as build_normalization_profile_registry,
    )
    from bioetl.domain.normalization.profiles.registry import (
        normalize_normalization_profile_coordinates as normalize_normalization_profile_coordinates,
    )
    from bioetl.domain.normalization.profiles.registry import (
        resolve_normalization_profile as resolve_normalization_profile,
    )
    from bioetl.domain.normalization.profiles.registry import (
        resolve_normalization_profile_identity as resolve_normalization_profile_identity,
    )
    from bioetl.domain.normalization.profiles.semanticscholar_publication import (
        SEMANTICSCHOLAR_PUBLICATION_PROFILE as SEMANTICSCHOLAR_PUBLICATION_PROFILE,
    )
    from bioetl.domain.normalization.profiles.semanticscholar_publication import (
        SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS as SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.uniprot_idmapping import (
        UNIPROT_IDMAPPING_PROFILE as UNIPROT_IDMAPPING_PROFILE,
    )
    from bioetl.domain.normalization.profiles.uniprot_idmapping import (
        UNIPROT_IDMAPPING_SCHEMA_FIELDS as UNIPROT_IDMAPPING_SCHEMA_FIELDS,
    )
    from bioetl.domain.normalization.profiles.uniprot_protein import (
        UNIPROT_PROTEIN_PROFILE as UNIPROT_PROTEIN_PROFILE,
    )
    from bioetl.domain.normalization.profiles.uniprot_protein import (
        UNIPROT_PROTEIN_SCHEMA_FIELDS as UNIPROT_PROTEIN_SCHEMA_FIELDS,
    )

_EXPORT_GROUPS: dict[str, tuple[str, ...]] = {
    "bioetl.domain.normalization.profiles.base": (
        "FieldRule",
        "FieldRuleIdentity",
        "NormalizationProfile",
        "NormalizationProfileIdentity",
    ),
    "bioetl.domain.normalization.profiles.chembl_activity": (
        "CHEMBL_ACTIVITY_PROFILE",
        "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_assay": (
        "CHEMBL_ASSAY_PROFILE",
        "CHEMBL_ASSAY_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_assay_parameters": (
        "CHEMBL_ASSAY_PARAMETERS_PROFILE",
        "CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_cell_line": (
        "CHEMBL_CELL_LINE_PROFILE",
        "CHEMBL_CELL_LINE_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_compound_record": (
        "CHEMBL_COMPOUND_RECORD_PROFILE",
        "CHEMBL_COMPOUND_RECORD_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_molecule": (
        "CHEMBL_MOLECULE_PROFILE",
        "CHEMBL_MOLECULE_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_protein_class": (
        "CHEMBL_PROTEIN_CLASS_PROFILE",
        "CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_publication": (
        "CHEMBL_PUBLICATION_PROFILE",
        "CHEMBL_PUBLICATION_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_publication_similarity": (
        "CHEMBL_PUBLICATION_SIMILARITY_PROFILE",
        "CHEMBL_PUBLICATION_SIMILARITY_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_publication_term": (
        "CHEMBL_PUBLICATION_TERM_PROFILE",
        "CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_subcellular_fraction": (
        "CHEMBL_SUBCELLULAR_FRACTION_PROFILE",
        "CHEMBL_SUBCELLULAR_FRACTION_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_target": (
        "CHEMBL_TARGET_PROFILE",
        "CHEMBL_TARGET_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_target_component": (
        "CHEMBL_TARGET_COMPONENT_PROFILE",
        "CHEMBL_TARGET_COMPONENT_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_target_protein_classification": (
        "CHEMBL_TARGET_PROTEIN_CLASSIFICATION_PROFILE",
        "CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.chembl_tissue": (
        "CHEMBL_TISSUE_PROFILE",
        "CHEMBL_TISSUE_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.crossref_publication": (
        "CROSSREF_PUBLICATION_PROFILE",
        "CROSSREF_PUBLICATION_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.openalex_publication": (
        "OPENALEX_PUBLICATION_PROFILE",
        "OPENALEX_PUBLICATION_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.pubchem_compound": (
        "PUBCHEM_COMPOUND_PROFILE",
        "PUBCHEM_COMPOUND_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.pubmed_publication": (
        "PUBMED_PUBLICATION_PROFILE",
        "PUBMED_PUBLICATION_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.registry": (
        "NORMALIZATION_PROFILE_REGISTRY",
        "build_normalization_profile_registry",
        "normalize_normalization_profile_coordinates",
        "resolve_normalization_profile",
        "resolve_normalization_profile_identity",
    ),
    "bioetl.domain.normalization.profiles.semanticscholar_publication": (
        "SEMANTICSCHOLAR_PUBLICATION_PROFILE",
        "SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.uniprot_idmapping": (
        "UNIPROT_IDMAPPING_PROFILE",
        "UNIPROT_IDMAPPING_SCHEMA_FIELDS",
    ),
    "bioetl.domain.normalization.profiles.uniprot_protein": (
        "UNIPROT_PROTEIN_PROFILE",
        "UNIPROT_PROTEIN_SCHEMA_FIELDS",
    ),
}

_EXPORT_MODULES = {
    export_name: module_name
    for module_name, export_names in _EXPORT_GROUPS.items()
    for export_name in export_names
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> object:  # pragma: no cover
    if TYPE_CHECKING:
        raise AttributeError
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
