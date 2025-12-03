"""Registry mapping field names to normalizer functions."""
from typing import Any, Callable

from bioetl.domain.transform.normalizers.identifiers import (
    normalize_bao_id,
    normalize_bao_label,
    normalize_chembl_id,
    normalize_doi,
    normalize_pcid,
    normalize_pmid,
    normalize_uniprot,
)
from bioetl.domain.transform.normalizers.collections import (
    normalize_cross_references,
    normalize_target_components,
)


CUSTOM_FIELD_NORMALIZERS: dict[str, Callable[[Any], Any]] = {
    # DOI variants
    "doi": normalize_doi,
    "doi_chembl": normalize_doi,
    # ChEMBL IDs
    "document_chembl_id": normalize_chembl_id,
    "assay_chembl_id": normalize_chembl_id,
    "molecule_chembl_id": normalize_chembl_id,
    "target_chembl_id": normalize_chembl_id,
    # PubMed
    "pubmed_id": normalize_pmid,
    "pmid": normalize_pmid,
    # PubChem
    "pcid": normalize_pcid,
    "pubchem_cid": normalize_pcid,
    # UniProt
    "uniprot_accession": normalize_uniprot,
    "uniprot_id": normalize_uniprot,
    "accession": normalize_uniprot,
    # BAO
    "bao_endpoint": normalize_bao_id,
    "bao_format": normalize_bao_id,
    "bao_label": normalize_bao_label,
    # Complex types
    "target_components": normalize_target_components,
    "cross_references": normalize_cross_references,
}


def register_normalizer(field_name: str, func: Callable[[Any], Any]) -> None:
    """Register a custom normalizer for a field."""
    CUSTOM_FIELD_NORMALIZERS[field_name] = func


def get_normalizer(field_name: str) -> Callable[[Any], Any] | None:
    """Get a custom normalizer for a field if one exists."""
    return CUSTOM_FIELD_NORMALIZERS.get(field_name)


__all__ = [
    "CUSTOM_FIELD_NORMALIZERS",
    "register_normalizer",
    "get_normalizer",
]
