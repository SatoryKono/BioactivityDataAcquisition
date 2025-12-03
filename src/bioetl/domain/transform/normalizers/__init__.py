"""
Normalizers package - domain-specific value normalization.

This package provides:
- Regex patterns for identifier validation
- Normalizer functions for identifiers (DOI, ChEMBL, PMID, etc.)
- Normalizers for collections (arrays, records)
- Field normalizer registry
"""
from bioetl.domain.transform.normalizers.base import (
    BAO_ID_REGEX,
    CHEMBL_ID_REGEX,
    DOI_REGEX,
    PUBCHEM_CID_REGEX,
    PUBMED_ID_REGEX,
    UNIPROT_ID_REGEX,
    is_missing,
)
from bioetl.domain.transform.normalizers.collections import (
    normalize_array,
    normalize_cross_references,
    normalize_record,
    normalize_target_components,
)
from bioetl.domain.transform.normalizers.identifiers import (
    normalize_bao_id,
    normalize_bao_label,
    normalize_chembl_id,
    normalize_doi,
    normalize_pcid,
    normalize_pmid,
    normalize_uniprot,
)
from bioetl.domain.transform.normalizers.registry import (
    CUSTOM_FIELD_NORMALIZERS,
)

__all__ = [
    # Regex patterns
    "DOI_REGEX",
    "CHEMBL_ID_REGEX",
    "PUBMED_ID_REGEX",
    "PUBCHEM_CID_REGEX",
    "UNIPROT_ID_REGEX",
    "BAO_ID_REGEX",
    # Base
    "is_missing",
    # Identifiers
    "normalize_doi",
    "normalize_chembl_id",
    "normalize_pmid",
    "normalize_pcid",
    "normalize_uniprot",
    "normalize_bao_id",
    "normalize_bao_label",
    # Collections
    "normalize_array",
    "normalize_record",
    "normalize_target_components",
    "normalize_cross_references",
    # Registry
    "CUSTOM_FIELD_NORMALIZERS",
]
