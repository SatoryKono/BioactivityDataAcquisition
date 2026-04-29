"""Pure canonicalizers for provider reference identifier surfaces."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from bioetl.domain.normalization.json import (
    deserialize_json_value,
    serialize_json_canonical,
)
from bioetl.domain.normalization.text import normalize_string

__all__ = [
    "normalize_chembl_reference_id",
    "normalize_drugbank_reference_id",
    "normalize_go_reference_id",
    "normalize_interpro_reference_id",
    "normalize_issn_reference_id",
    "normalize_json_array_reference_ids",
    "normalize_json_object_reference_id",
    "normalize_json_string_reference_ids",
    "normalize_openalex_reference_id",
    "normalize_orcid_reference_id",
    "normalize_pdb_reference_id",
    "normalize_pfam_reference_id",
    "normalize_reactome_reference_id",
    "normalize_ror_reference_id",
    "normalize_semantic_scholar_reference_id",
    "normalize_uniprot_accession_reference_id",
]

ReferenceNormalizer = Callable[[object], object]

_GO_RE = re.compile(r"^GO[:_\s-]?(\d{7})$", re.IGNORECASE)
_INTERPRO_RE = re.compile(r"^IPR[:_\s-]?(\d{6})$", re.IGNORECASE)
_PFAM_RE = re.compile(r"^PF[:_\s-]?(\d{5})$", re.IGNORECASE)
_REACTOME_RE = re.compile(r"^R-([A-Za-z0-9]+)-(\d+)$", re.IGNORECASE)
_PDB_RE = re.compile(r"^[A-Za-z0-9]{4}$")
_ORCID_RE = re.compile(r"^\d{15}[\dX]$", re.IGNORECASE)
_ISSN_RE = re.compile(r"^\d{7}[\dX]$", re.IGNORECASE)
_UNIPROT_ACCESSION_RE = re.compile(r"^[A-Z0-9]{6,10}(?:-\d+)?$", re.IGNORECASE)
_CHEMBL_ID_RE = re.compile(r"^CHEMBL(\d+)$", re.IGNORECASE)
_DRUGBANK_ID_RE = re.compile(r"^DB(\d{5})$", re.IGNORECASE)
_S2_HEX_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)

_OBO_IRI_PREFIXES = (
    "https://purl.obolibrary.org/obo/",
    "http://purl.obolibrary.org/obo/",
)
_INTERPRO_PREFIXES = (
    "https://www.ebi.ac.uk/interpro/entry/interpro/",
    "http://www.ebi.ac.uk/interpro/entry/interpro/",
)
_PFAM_PREFIXES = (
    "https://pfam.xfam.org/family/",
    "http://pfam.xfam.org/family/",
)
_REACTOME_PREFIXES = (
    "https://reactome.org/content/detail/",
    "http://reactome.org/content/detail/",
)
_PDB_PREFIXES = (
    "https://www.rcsb.org/structure/",
    "http://www.rcsb.org/structure/",
)
_ORCID_PREFIXES = (
    "https://orcid.org/",
    "http://orcid.org/",
    "orcid.org/",
)
_ISSN_PREFIXES = ("urn:issn:", "issn:")
_ROR_PREFIXES = ("https://ror.org/", "http://ror.org/", "ror.org/")
_OPENALEX_PREFIXES = ("https://openalex.org/", "http://openalex.org/")
_SEMANTIC_SCHOLAR_PREFIXES = (
    "https://www.semanticscholar.org/paper/",
    "http://www.semanticscholar.org/paper/",
    "https://www.semanticscholar.org/author/",
    "http://www.semanticscholar.org/author/",
)


def _normalized_text(value: object) -> str | None:
    return normalize_string(value) if isinstance(value, str) else None


def _strip_prefixes(value: str, prefixes: tuple[str, ...]) -> str:
    lowered = value.casefold()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return value[len(prefix) :].strip().strip("/")
    return value.strip().strip("/")


def _canonical_or_text(
    value: object,
    *,
    normalizer: Callable[[str], str | None],
) -> object:
    text = _normalized_text(value)
    if text is None:
        return None if isinstance(value, str) or value is None else value
    return normalizer(text) or text


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
    return "-".join(
        (compact[0:4], compact[4:8], compact[8:12], compact[12:16])
    )


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


def normalize_openalex_reference_id(value: object, *, prefix: str) -> object:
    """Normalize OpenAlex reference IDs from URLs or bare IDs."""
    text = _normalized_text(value)
    if text is None:
        return None if isinstance(value, str) or value is None else value
    candidate = _strip_prefixes(text, _OPENALEX_PREFIXES)
    return _normalize_openalex_candidate(candidate, prefix=prefix) or text


def _normalize_openalex_candidate(candidate: str, *, prefix: str) -> str | None:
    normalized_prefix = prefix.upper()
    if not candidate.upper().startswith(normalized_prefix):
        return None
    suffix = candidate[len(normalized_prefix) :]
    return f"{normalized_prefix}{suffix}" if suffix.isdigit() else None


def normalize_json_array_reference_ids(
    value: object,
    *,
    id_normalizer: ReferenceNormalizer,
    sort_items: bool = True,
) -> object:
    """Canonicalize a JSON array of reference dicts by normalizing each ``id``."""
    parsed = _parse_json_array(value)
    if parsed is None:
        return _json_fallback(value)
    normalized = [_normalize_reference_item(item, id_normalizer) for item in parsed]
    return serialize_json_canonical(_sort_reference_items(normalized) if sort_items else normalized)


def normalize_json_string_reference_ids(
    value: object,
    *,
    item_normalizer: ReferenceNormalizer,
    sort_items: bool = True,
) -> object:
    """Canonicalize a JSON string-list of provider reference IDs."""
    parsed = _parse_json_array(value)
    if parsed is None:
        return _json_fallback(value)
    normalized = [item_normalizer(item) for item in parsed]
    if sort_items:
        normalized = _dedupe_reference_items(_sort_reference_items(normalized))
    return serialize_json_canonical(normalized)


def normalize_json_object_reference_id(
    value: object,
    *,
    id_normalizer: ReferenceNormalizer,
) -> object:
    """Canonicalize a JSON object by normalizing its ``id`` field."""
    parsed = _parse_json_object(value)
    if parsed is None:
        return _json_fallback(value)
    return serialize_json_canonical(_normalize_reference_item(parsed, id_normalizer))


def _parse_json_array(value: object) -> list[object] | None:
    parsed = _parse_json_value(value)
    return parsed if isinstance(parsed, list) else None


def _parse_json_object(value: object) -> dict[str, object] | None:
    parsed = _parse_json_value(value)
    return dict(parsed) if isinstance(parsed, Mapping) else None


def _parse_json_value(value: object) -> object:
    if isinstance(value, str):
        return _parse_json_text(value)
    return value


def _parse_json_text(value: str) -> object:
    normalized = normalize_string(value)
    if normalized is None:
        return None
    try:
        return deserialize_json_value(normalized)
    except ValueError:
        return None


def _normalize_reference_item(
    item: object,
    id_normalizer: ReferenceNormalizer,
) -> object:
    if not isinstance(item, Mapping):
        return item
    normalized = dict(item)
    if "id" in normalized:
        normalized["id"] = id_normalizer(normalized["id"])
    return normalized


def _sort_reference_items(items: list[object]) -> list[object]:
    return sorted(items, key=lambda item: serialize_json_canonical({"value": item}))


def _dedupe_reference_items(items: list[object]) -> list[object]:
    seen: set[str] = set()
    deduped: list[object] = []
    for item in items:
        key = serialize_json_canonical({"value": item})
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _json_fallback(value: object) -> object:
    if not isinstance(value, str):
        return value
    return normalize_string(value)
