"""Provider/entity normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_activity import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.chembl_molecule import (
    CHEMBL_MOLECULE_PROFILE,
    CHEMBL_MOLECULE_SCHEMA_FIELDS,
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
)
from bioetl.domain.normalization.profiles.semanticscholar_publication import (
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.uniprot_protein import (
    UNIPROT_PROTEIN_PROFILE,
    UNIPROT_PROTEIN_SCHEMA_FIELDS,
)

__all__ = [
    "CHEMBL_ACTIVITY_PROFILE",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
    "CHEMBL_MOLECULE_PROFILE",
    "CHEMBL_MOLECULE_SCHEMA_FIELDS",
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
    "UNIPROT_PROTEIN_PROFILE",
    "UNIPROT_PROTEIN_SCHEMA_FIELDS",
    "FieldRule",
    "NormalizationProfile",
    "build_normalization_profile_registry",
    "normalize_normalization_profile_coordinates",
    "resolve_normalization_profile",
]
