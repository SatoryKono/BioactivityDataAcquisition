"""Provider/entity normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.profiles.base import (
    FieldRule,
    FieldRuleIdentity,
    NormalizationProfile,
    NormalizationProfileIdentity,
)
from bioetl.domain.normalization.profiles.chembl_activity import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_assay import (
    CHEMBL_ASSAY_PROFILE,
    CHEMBL_ASSAY_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_assay_parameters import (
    CHEMBL_ASSAY_PARAMETERS_PROFILE,
    CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_cell_line import (
    CHEMBL_CELL_LINE_PROFILE,
    CHEMBL_CELL_LINE_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_compound_record import (
    CHEMBL_COMPOUND_RECORD_PROFILE,
    CHEMBL_COMPOUND_RECORD_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_molecule import (
    CHEMBL_MOLECULE_PROFILE,
    CHEMBL_MOLECULE_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_protein_class import (
    CHEMBL_PROTEIN_CLASS_PROFILE,
    CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_publication import (
    CHEMBL_PUBLICATION_PROFILE,
    CHEMBL_PUBLICATION_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_publication_similarity import (
    CHEMBL_PUBLICATION_SIMILARITY_PROFILE,
    CHEMBL_PUBLICATION_SIMILARITY_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_publication_term import (
    CHEMBL_PUBLICATION_TERM_PROFILE,
    CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_subcellular_fraction import (
    CHEMBL_SUBCELLULAR_FRACTION_PROFILE,
    CHEMBL_SUBCELLULAR_FRACTION_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_target import (
    CHEMBL_TARGET_PROFILE,
    CHEMBL_TARGET_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_target_component import (
    CHEMBL_TARGET_COMPONENT_PROFILE,
    CHEMBL_TARGET_COMPONENT_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_tissue import (
    CHEMBL_TISSUE_PROFILE,
    CHEMBL_TISSUE_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.crossref_publication import (
    CROSSREF_PUBLICATION_PROFILE,
    CROSSREF_PUBLICATION_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.openalex_publication import (
    OPENALEX_PUBLICATION_PROFILE,
    OPENALEX_PUBLICATION_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.pubchem_compound import (
    PUBCHEM_COMPOUND_PROFILE,
    PUBCHEM_COMPOUND_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.pubmed_publication import (
    PUBMED_PUBLICATION_PROFILE,
    PUBMED_PUBLICATION_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.registry import (
    NORMALIZATION_PROFILE_REGISTRY,
    build_normalization_profile_registry,
    normalize_normalization_profile_coordinates,
    resolve_normalization_profile,
    resolve_normalization_profile_identity,
)
from bioetl.domain.normalization.profiles.semanticscholar_publication import (
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.uniprot_idmapping import (
    UNIPROT_IDMAPPING_PROFILE,
    UNIPROT_IDMAPPING_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.uniprot_protein import (
    UNIPROT_PROTEIN_PROFILE,
    UNIPROT_PROTEIN_SCHEMA_FIELDS,
)

__all__ = [
    "CHEMBL_ACTIVITY_PROFILE",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
    "CHEMBL_ASSAY_PARAMETERS_PROFILE",
    "CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS",
    "CHEMBL_ASSAY_PROFILE",
    "CHEMBL_ASSAY_SCHEMA_FIELDS",
    "CHEMBL_CELL_LINE_PROFILE",
    "CHEMBL_CELL_LINE_SCHEMA_FIELDS",
    "CHEMBL_COMPOUND_RECORD_PROFILE",
    "CHEMBL_COMPOUND_RECORD_SCHEMA_FIELDS",
    "CHEMBL_MOLECULE_PROFILE",
    "CHEMBL_MOLECULE_SCHEMA_FIELDS",
    "CHEMBL_PROTEIN_CLASS_PROFILE",
    "CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS",
    "CHEMBL_PUBLICATION_PROFILE",
    "CHEMBL_PUBLICATION_SCHEMA_FIELDS",
    "CHEMBL_PUBLICATION_SIMILARITY_PROFILE",
    "CHEMBL_PUBLICATION_SIMILARITY_SCHEMA_FIELDS",
    "CHEMBL_PUBLICATION_TERM_PROFILE",
    "CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS",
    "CHEMBL_SUBCELLULAR_FRACTION_PROFILE",
    "CHEMBL_SUBCELLULAR_FRACTION_SCHEMA_FIELDS",
    "CHEMBL_TARGET_COMPONENT_PROFILE",
    "CHEMBL_TARGET_COMPONENT_SCHEMA_FIELDS",
    "CHEMBL_TARGET_PROFILE",
    "CHEMBL_TARGET_SCHEMA_FIELDS",
    "CHEMBL_TISSUE_PROFILE",
    "CHEMBL_TISSUE_SCHEMA_FIELDS",
    "CROSSREF_PUBLICATION_PROFILE",
    "CROSSREF_PUBLICATION_SCHEMA_FIELDS",
    "NORMALIZATION_PROFILE_REGISTRY",
    "OPENALEX_PUBLICATION_PROFILE",
    "OPENALEX_PUBLICATION_SCHEMA_FIELDS",
    "PUBCHEM_COMPOUND_PROFILE",
    "PUBCHEM_COMPOUND_SCHEMA_FIELDS",
    "PUBMED_PUBLICATION_PROFILE",
    "PUBMED_PUBLICATION_SCHEMA_FIELDS",
    "SEMANTICSCHOLAR_PUBLICATION_PROFILE",
    "SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS",
    "UNIPROT_IDMAPPING_PROFILE",
    "UNIPROT_IDMAPPING_SCHEMA_FIELDS",
    "UNIPROT_PROTEIN_PROFILE",
    "UNIPROT_PROTEIN_SCHEMA_FIELDS",
    "FieldRule",
    "FieldRuleIdentity",
    "NormalizationProfile",
    "NormalizationProfileIdentity",
    "build_normalization_profile_registry",
    "normalize_normalization_profile_coordinates",
    "resolve_normalization_profile",
    "resolve_normalization_profile_identity",
]
