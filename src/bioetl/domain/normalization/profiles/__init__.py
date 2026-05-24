"""Provider/entity normalization profiles.

This facade preserves ``from bioetl.domain.normalization.profiles import X``
imports without eagerly importing every shipped normalization profile.
"""

from __future__ import annotations

from importlib import import_module

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


def __getattr__(name: str) -> object:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
