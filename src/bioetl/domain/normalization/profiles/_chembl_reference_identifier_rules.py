"""Shared ChEMBL reference-identifier rule wiring for normalization profiles."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.normalization.profiles.chembl_policy_registry import (
    chembl_reference_identifier_family_fields,
)
from bioetl.domain.normalization.profiles._standard_profile_rule_components import (
    RuleComponentSpec,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_chembl_id,
    normalize_profile_doi,
    normalize_profile_mesh_id,
    normalize_profile_ncbi_taxonomy_id,
    normalize_profile_pmc_id,
    normalize_profile_pmid,
    normalize_profile_uniprot_accession,
    normalize_profile_uniprot_accessions_ordered,
)

__all__ = ["chembl_reference_identifier_rules"]

_FieldNormalizer = Callable[[object], object]

_SCALAR_NORMALIZERS: dict[str, _FieldNormalizer] = {
    "chembl": normalize_profile_chembl_id,
    "doi": normalize_profile_doi,
    "mesh": normalize_profile_mesh_id,
    "ncbi_taxonomy": normalize_profile_ncbi_taxonomy_id,
    "pmcid": normalize_profile_pmc_id,
    "pmid": normalize_profile_pmid,
    "uniprot_accession": normalize_profile_uniprot_accession,
}
_FIELD_NORMALIZER_OVERRIDES: dict[str, _FieldNormalizer] = {
    "component_accessions": normalize_profile_uniprot_accessions_ordered,
}
_FAMILY_NOTES: dict[str, str] = {
    "chembl": "Canonicalize ChEMBL identifiers through the shared ChEMBL reference-ID policy.",
    "doi": "Canonicalize DOI identifiers through the shared ChEMBL reference-ID policy.",
    "mesh": "Canonicalize MeSH identifiers through the shared ChEMBL reference-ID policy.",
    "ncbi_taxonomy": "Canonicalize NCBI Taxonomy identifiers through the shared ChEMBL reference-ID policy.",
    "pmcid": "Canonicalize PMCID identifiers through the shared ChEMBL reference-ID policy.",
    "pmid": "Canonicalize PMID identifiers through the shared ChEMBL reference-ID policy.",
    "uniprot_accession": "Canonicalize UniProt-like accessions through the shared ChEMBL reference-ID policy.",
}


def chembl_reference_identifier_rules(entity: str) -> dict[str, RuleComponentSpec]:
    """Return profile special rules backed by shared ChEMBL reference-ID policy."""
    rules: dict[str, RuleComponentSpec] = {}
    for family_name, scalar_normalizer in _SCALAR_NORMALIZERS.items():
        for field_name in chembl_reference_identifier_family_fields(
            family_name,
            entity=entity,
        ):
            normalizer = _FIELD_NORMALIZER_OVERRIDES.get(
                field_name,
                scalar_normalizer,
            )
            rules[field_name] = (normalizer, _FAMILY_NOTES[family_name])
    return rules
