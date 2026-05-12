"""Pure canonicalizers for provider reference identifier surfaces."""

from __future__ import annotations

from bioetl.domain.normalization._reference_id_json_normalizers import (
    normalize_json_array_reference_ids,
    normalize_json_object_reference_id,
    normalize_json_string_reference_ids,
)
from bioetl.domain.normalization._reference_id_ncbi_taxonomy import (
    normalize_ncbi_taxonomy_reference_id,
)
from bioetl.domain.normalization._reference_id_normalizers import (
    normalize_chembl_reference_id,
    normalize_drugbank_reference_id,
    normalize_go_reference_id,
    normalize_interpro_reference_id,
    normalize_issn_reference_id,
    normalize_mesh_reference_id,
    normalize_orcid_reference_id,
    normalize_pdb_reference_id,
    normalize_pfam_reference_id,
    normalize_pmcid_reference_id,
    normalize_reactome_reference_id,
    normalize_ror_reference_id,
    normalize_semantic_scholar_reference_id,
    normalize_uniprot_accession_reference_id,
)
from bioetl.domain.normalization._reference_id_openalex import (
    normalize_openalex_author_reference_id as _normalize_openalex_author_reference_id,
)
from bioetl.domain.normalization._reference_id_openalex import (
    normalize_openalex_institution_reference_id as _normalize_openalex_institution_reference_id,
)
from bioetl.domain.normalization._reference_id_openalex import (
    normalize_openalex_reference_id,
)
from bioetl.domain.normalization._reference_id_openalex import (
    normalize_openalex_topic_reference_id as _normalize_openalex_topic_reference_id,
)
from bioetl.domain.normalization._reference_id_openalex import (
    normalize_openalex_work_reference_id as _normalize_openalex_work_reference_id,
)
from bioetl.domain.normalization._reference_id_registry import (
    ReferenceIdentifierFamily,
    ReferenceNormalizer,
    build_reference_identifier_families,
)
from bioetl.domain.normalization._reference_id_support import (
    _CHEMBL_ID_RE,
    _canonical_or_text,
    _normalized_text,
    _strip_prefixes,
)
from bioetl.domain.normalization.identifiers import normalize_doi, normalize_pmid

__all__ = [
    "ReferenceIdentifierFamily",
    "ReferenceNormalizer",
    "normalize_chembl_reference_id",
    "normalize_doi_reference_id",
    "normalize_drugbank_reference_id",
    "normalize_go_reference_id",
    "normalize_interpro_reference_id",
    "normalize_issn_reference_id",
    "normalize_json_array_reference_ids",
    "normalize_json_object_reference_id",
    "normalize_json_string_reference_ids",
    "normalize_mesh_reference_id",
    "normalize_ncbi_taxonomy_reference_id",
    "normalize_openalex_reference_id",
    "normalize_orcid_reference_id",
    "normalize_pdb_reference_id",
    "normalize_pfam_reference_id",
    "normalize_pmcid_reference_id",
    "normalize_pmid_reference_id",
    "normalize_reactome_reference_id",
    "normalize_ror_reference_id",
    "normalize_semantic_scholar_reference_id",
    "normalize_uniprot_accession_reference_id",
    "normalize_uniprot_mixed_mapping_reference_id",
    "reference_identifier_families",
    "reference_identifier_family",
]


def normalize_uniprot_mixed_mapping_reference_id(value: object) -> object:
    """Normalize one mixed UniProt mapping token across known ID families.

    ``uniprot_idmapping.all_mappings`` is not a pure UniProt accession list.
    It primarily carries accessions, but tracked edge cases also include other
    provider IDs such as ChEMBL anchors. The normalizer therefore tries the
    canonical governed families in descending specificity and otherwise
    preserves the normalized source text.
    """
    text = _normalized_text(value)
    if text is None:
        return None if value is None else value
    return (
        _normalize_mixed_mapping_chembl(text)
        or _normalize_mixed_mapping_fallback(text)
        or text
    )


def _normalize_mixed_mapping_chembl(text: str) -> str | None:
    chembl_match = _CHEMBL_ID_RE.fullmatch(text.strip())
    if chembl_match is None:
        return None
    return f"CHEMBL{int(chembl_match.group(1))}"


def _normalize_mixed_mapping_fallback(text: str) -> object | None:
    from bioetl.domain.normalization._reference_id_normalizers import (
        normalize_drugbank_reference_id,
        normalize_uniprot_accession_reference_id,
    )

    for normalizer in (
        normalize_uniprot_accession_reference_id,
        normalize_drugbank_reference_id,
    ):
        normalized = normalizer(text)
        if normalized != text:
            return normalized
    return None


def normalize_doi_reference_id(value: object) -> object:
    """Normalize DOI references to lowercase bare DOI text."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    return normalize_doi(value)


def normalize_pmid_reference_id(value: object) -> object:
    """Normalize PubMed references to canonical digits-only PMID text."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str | int):
        return normalize_pmid(value)
    return value


_REFERENCE_IDENTIFIER_FAMILIES = build_reference_identifier_families(
    {
        "orcid": normalize_orcid_reference_id,
        "issn": normalize_issn_reference_id,
        "ror": normalize_ror_reference_id,
        "openalex_author": _normalize_openalex_author_reference_id,
        "openalex_institution": _normalize_openalex_institution_reference_id,
        "openalex_topic": _normalize_openalex_topic_reference_id,
        "openalex_work": _normalize_openalex_work_reference_id,
        "semantic_scholar_author": normalize_semantic_scholar_reference_id,
        "semantic_scholar_paper": normalize_semantic_scholar_reference_id,
        "ncbi_taxonomy": normalize_ncbi_taxonomy_reference_id,
        "uniprot_accession": normalize_uniprot_accession_reference_id,
        "mixed_identifier_set": normalize_uniprot_mixed_mapping_reference_id,
        "go": normalize_go_reference_id,
        "interpro": normalize_interpro_reference_id,
        "pfam": normalize_pfam_reference_id,
        "reactome": normalize_reactome_reference_id,
        "pdb": normalize_pdb_reference_id,
        "chembl": normalize_chembl_reference_id,
        "doi": normalize_doi_reference_id,
        "pmid": normalize_pmid_reference_id,
        "pmcid": normalize_pmcid_reference_id,
        "mesh": normalize_mesh_reference_id,
        "drugbank": normalize_drugbank_reference_id,
    }
)
_REFERENCE_IDENTIFIER_FAMILY_BY_NAME = {
    family.name: family for family in _REFERENCE_IDENTIFIER_FAMILIES
}


def reference_identifier_families() -> tuple[ReferenceIdentifierFamily, ...]:
    """Return the governed reference identifier families used by profiles."""
    return _REFERENCE_IDENTIFIER_FAMILIES


def reference_identifier_family(name: str) -> ReferenceIdentifierFamily:
    """Return one governed reference identifier family by stable registry name."""
    return _REFERENCE_IDENTIFIER_FAMILY_BY_NAME[name]
