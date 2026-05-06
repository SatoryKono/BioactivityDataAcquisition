"""Pure canonicalizers for provider reference identifier surfaces."""

from __future__ import annotations

from bioetl.domain.normalization._reference_id_json_normalizers import (
    normalize_json_array_reference_ids,
    normalize_json_object_reference_id,
    normalize_json_string_reference_ids,
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
    _DRUGBANK_ID_RE,
    _GO_RE,
    _INTERPRO_PREFIXES,
    _INTERPRO_RE,
    _ISSN_PREFIXES,
    _ISSN_RE,
    _MESH_PREFIXES,
    _MESH_RE,
    _NCBI_TAXONOMY_PREFIXES,
    _NCBI_TAXONOMY_RE,
    _OBO_IRI_PREFIXES,
    _ORCID_PREFIXES,
    _ORCID_RE,
    _PDB_PREFIXES,
    _PDB_RE,
    _PFAM_PREFIXES,
    _PFAM_RE,
    _PMCID_PREFIXES,
    _PMCID_RE,
    _REACTOME_PREFIXES,
    _REACTOME_RE,
    _ROR_PREFIXES,
    _S2_HEX_RE,
    _SEMANTIC_SCHOLAR_PREFIXES,
    _UNIPROT_ACCESSION_RE,
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
    "reference_identifier_families",
    "reference_identifier_family",
]


def _normalize_go_text(value: str) -> str | None:
    match = _GO_RE.fullmatch(_strip_prefixes(value, _OBO_IRI_PREFIXES))
    return f"GO:{match.group(1)}" if match else None


def normalize_go_reference_id(value: object) -> object:
    """Normalize GO references to ``GO:0000000`` while preserving unknowns."""
    return _canonical_or_text(value, normalizer=_normalize_go_text)


def _normalize_interpro_text(value: str) -> str | None:
    match = _INTERPRO_RE.fullmatch(_strip_prefixes(value, _INTERPRO_PREFIXES))
    return f"IPR{match.group(1)}" if match else None


def normalize_interpro_reference_id(value: object) -> object:
    """Normalize InterPro references to ``IPR000000`` while preserving unknowns."""
    return _canonical_or_text(value, normalizer=_normalize_interpro_text)


def _normalize_pfam_text(value: str) -> str | None:
    match = _PFAM_RE.fullmatch(_strip_prefixes(value, _PFAM_PREFIXES))
    return f"PF{match.group(1)}" if match else None


def normalize_pfam_reference_id(value: object) -> object:
    """Normalize Pfam references to ``PF00000`` while preserving unknowns."""
    return _canonical_or_text(value, normalizer=_normalize_pfam_text)


def _normalize_reactome_text(value: str) -> str | None:
    match = _REACTOME_RE.fullmatch(_strip_prefixes(value, _REACTOME_PREFIXES))
    return f"R-{match.group(1).upper()}-{match.group(2)}" if match else None


def normalize_reactome_reference_id(value: object) -> object:
    """Normalize Reactome references to uppercase stable pathway IDs."""
    return _canonical_or_text(value, normalizer=_normalize_reactome_text)


def _normalize_pdb_text(value: str) -> str | None:
    candidate = _strip_prefixes(value, _PDB_PREFIXES)
    return candidate.upper() if _PDB_RE.fullmatch(candidate) else None


def normalize_pdb_reference_id(value: object) -> object:
    """Normalize PDB references to uppercase 4-character IDs."""
    return _canonical_or_text(value, normalizer=_normalize_pdb_text)


def _normalize_orcid_text(value: str) -> str | None:
    candidate = _strip_prefixes(value, _ORCID_PREFIXES)
    compact = candidate.replace("-", "").replace(" ", "").upper()
    if not _ORCID_RE.fullmatch(compact):
        return None
    return "-".join((compact[0:4], compact[4:8], compact[8:12], compact[12:16]))


def normalize_orcid_reference_id(value: object) -> object:
    """Normalize ORCID references to hyphenated canonical ORCID IDs."""
    return _canonical_or_text(value, normalizer=_normalize_orcid_text)


def _normalize_issn_text(value: str) -> str | None:
    candidate = _strip_prefixes(value, _ISSN_PREFIXES)
    compact = candidate.replace("-", "").replace(" ", "").upper()
    if not _ISSN_RE.fullmatch(compact):
        return None
    return f"{compact[0:4]}-{compact[4:8]}"


def normalize_issn_reference_id(value: object) -> object:
    """Normalize ISSN values to ``1234-567X`` canonical form."""
    return _canonical_or_text(value, normalizer=_normalize_issn_text)


def _normalize_uniprot_accession_text(value: str) -> str | None:
    candidate = value.strip().upper()
    return candidate if _UNIPROT_ACCESSION_RE.fullmatch(candidate) else None


def normalize_uniprot_accession_reference_id(value: object) -> object:
    """Normalize UniProt accessions to uppercase canonical accession text."""
    return _canonical_or_text(value, normalizer=_normalize_uniprot_accession_text)


def _normalize_chembl_text(value: str) -> str | None:
    match = _CHEMBL_ID_RE.fullmatch(value.strip())
    return f"CHEMBL{match.group(1)}" if match else None


def normalize_chembl_reference_id(value: object) -> object:
    """Normalize ChEMBL identifiers to uppercase ``CHEMBL`` prefixed IDs."""
    return _canonical_or_text(value, normalizer=_normalize_chembl_text)


def _normalize_ncbi_taxonomy_text(value: str) -> int | None:
    candidate = _strip_prefixes(value, _NCBI_TAXONOMY_PREFIXES)
    if not _NCBI_TAXONOMY_RE.fullmatch(candidate):
        return None
    taxonomy_id = int(candidate)
    return taxonomy_id if taxonomy_id > 0 else None


def normalize_ncbi_taxonomy_reference_id(value: object) -> object:
    """Normalize NCBI Taxonomy identifiers to positive integer scalar form."""
    if value is None or isinstance(value, bool):
        return None
    numeric_normalized = _normalize_ncbi_taxonomy_numeric(value)
    if numeric_normalized is not None:
        return numeric_normalized
    text = _normalized_text(value)
    if text is None:
        return value
    return _normalize_ncbi_taxonomy_text(text) or text


def _normalize_ncbi_taxonomy_numeric(value: object) -> object | None:
    """Normalize numeric NCBI taxonomy representations when possible."""
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        return int(value) if value.is_integer() and value > 0 else value
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


def _normalize_pmcid_text(value: str) -> str | None:
    candidate = _strip_prefixes(value, _PMCID_PREFIXES)
    match = _PMCID_RE.fullmatch(candidate)
    return f"PMC{match.group(1)}" if match else None


def normalize_pmcid_reference_id(value: object) -> object:
    """Normalize PubMed Central references to uppercase ``PMC`` identifiers."""
    return _canonical_or_text(value, normalizer=_normalize_pmcid_text)


def _normalize_mesh_text(value: str) -> str | None:
    candidate = _strip_prefixes(value, _MESH_PREFIXES).replace(" ", "").upper()
    return candidate if _MESH_RE.fullmatch(candidate) else None


def normalize_mesh_reference_id(value: object) -> object:
    """Normalize MeSH descriptor references to uppercase descriptor IDs."""
    return _canonical_or_text(value, normalizer=_normalize_mesh_text)


def _normalize_drugbank_text(value: str) -> str | None:
    match = _DRUGBANK_ID_RE.fullmatch(value.strip())
    return f"DB{match.group(1)}" if match else None


def normalize_drugbank_reference_id(value: object) -> object:
    """Normalize DrugBank identifiers to uppercase ``DB00000`` form."""
    return _canonical_or_text(value, normalizer=_normalize_drugbank_text)


def _normalize_semantic_scholar_text(value: str) -> str | None:
    candidate = _strip_prefixes(value, _SEMANTIC_SCHOLAR_PREFIXES)
    return candidate.casefold() if _S2_HEX_RE.fullmatch(candidate) else None


def normalize_semantic_scholar_reference_id(value: object) -> object:
    """Normalize Semantic Scholar paper/author IDs when they are stable hex IDs."""
    return _canonical_or_text(value, normalizer=_normalize_semantic_scholar_text)


def normalize_ror_reference_id(value: object) -> object:
    """Normalize ROR references to canonical ``https://ror.org/...`` URLs."""
    text = _normalized_text(value)
    if text is None:
        return None if isinstance(value, str) or value is None else value
    suffix = _strip_prefixes(text, _ROR_PREFIXES).casefold()
    return f"https://ror.org/{suffix}" if suffix else None


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
