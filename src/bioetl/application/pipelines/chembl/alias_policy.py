"""Versioned ChEMBL alias policy for provider and contract boundaries."""

from __future__ import annotations

from collections.abc import Mapping

__all__ = [
    "CHEMBL_ALIAS_POLICY_VERSION",
    "CHEMBL_BRONZE_PROVIDER_ALIASES",
    "CHEMBL_GOLD_PUBLICATION_IDENTIFIER_PROJECTIONS",
    "get_bronze_provider_aliases",
]

CHEMBL_ALIAS_POLICY_VERSION = "chembl-alias-policy.v1"

# Provider-native Bronze payload aliases. These are applied at the transformer
# ingestion boundary only, before canonical Silver records are constructed.
CHEMBL_BRONZE_PROVIDER_ALIASES: Mapping[str, Mapping[str, str]] = {
    "activity": {
        "molecule_id": "molecule_chembl_id",
    },
    "tissue": {
        "tissue_id": "tissue_chembl_id",
    },
}

# Gold/publication contract projections. These remain separate from Bronze
# provider aliases because they bridge published publication identifier names.
CHEMBL_GOLD_PUBLICATION_IDENTIFIER_PROJECTIONS: Mapping[str, tuple[str, ...]] = {
    "publication_doi": ("publication_doi", "doi", "document_doi"),
    "publication_pmid": (
        "publication_pmid",
        "pmid",
        "pubmed_id",
        "document_pubmed_id",
    ),
    "publication_pmc_id": ("publication_pmc_id", "pmc_id", "document_pmc_id"),
}


def get_bronze_provider_aliases(entity: str) -> Mapping[str, str]:
    """Return provider-native Bronze aliases for one ChEMBL entity."""
    return CHEMBL_BRONZE_PROVIDER_ALIASES.get(entity, {})
