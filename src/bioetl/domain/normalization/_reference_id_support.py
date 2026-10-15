"""Shared pure helpers for provider reference identifier normalization."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from bioetl.domain.normalization.json import (
    deserialize_json_value,
    serialize_json_canonical,
)
from bioetl.domain.normalization.text import normalize_string

_GO_RE = re.compile(r"^GO[:_\s-]?(\d{7})$", re.IGNORECASE)
_INTERPRO_RE = re.compile(r"^IPR[:_\s-]?(\d{6})$", re.IGNORECASE)
_PFAM_RE = re.compile(r"^PF[:_\s-]?(\d{5})$", re.IGNORECASE)
_REACTOME_RE = re.compile(r"^R-([A-Z0-9]+)-(\d+)$", re.IGNORECASE)
_PDB_RE = re.compile(r"^[A-Za-z0-9]{4}$")
_ORCID_RE = re.compile(r"^\d{15}[\dX]$", re.IGNORECASE)
_ISSN_RE = re.compile(r"^\d{7}[\dX]$", re.IGNORECASE)
_UNIPROT_ACCESSION_RE = re.compile(r"^[A-Z0-9]{6,10}(?:-\d+)?$", re.IGNORECASE)
_CHEMBL_ID_RE = re.compile(r"^CHEMBL(\d+)$", re.IGNORECASE)
_DRUGBANK_ID_RE = re.compile(r"^DB(\d{5})$", re.IGNORECASE)
_S2_HEX_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
_NCBI_TAXONOMY_RE = re.compile(r"^\d{1,10}$")
_PMCID_RE = re.compile(r"^(?:PMC)?(\d+)$", re.IGNORECASE)
_MESH_RE = re.compile(r"^[A-Z]\d{6}$", re.IGNORECASE)


def _legacy_transport_alias(secure_prefix: str) -> str:
    return "http" + secure_prefix.removeprefix("https")


def _with_legacy_transport_aliases(*secure_prefixes: str) -> tuple[str, ...]:
    aliases: list[str] = []
    for secure_prefix in secure_prefixes:
        aliases.extend((secure_prefix, _legacy_transport_alias(secure_prefix)))
    return tuple(aliases)


_OBO_IRI_PREFIXES = _with_legacy_transport_aliases("https://purl.obolibrary.org/obo/")
_INTERPRO_PREFIXES = _with_legacy_transport_aliases(
    "https://www.ebi.ac.uk/interpro/entry/interpro/"
)
_PFAM_PREFIXES = _with_legacy_transport_aliases("https://pfam.xfam.org/family/")
_REACTOME_PREFIXES = _with_legacy_transport_aliases(
    "https://reactome.org/content/detail/"
)
_PDB_PREFIXES = _with_legacy_transport_aliases("https://www.rcsb.org/structure/")
_ORCID_PREFIXES = (
    *_with_legacy_transport_aliases("https://orcid.org/"),
    "orcid.org/",
)
_ISSN_PREFIXES = ("urn:issn:", "issn:")
_ROR_PREFIXES = (
    *_with_legacy_transport_aliases("https://ror.org/"),
    "ror.org/",
)
_OPENALEX_PREFIXES = _with_legacy_transport_aliases("https://openalex.org/")
_SEMANTIC_SCHOLAR_PREFIXES = _with_legacy_transport_aliases(
    "https://www.semanticscholar.org/paper/",
    "https://www.semanticscholar.org/author/",
)
_NCBI_TAXONOMY_PREFIXES = (
    *_with_legacy_transport_aliases("https://www.ncbi.nlm.nih.gov/taxonomy/"),
    "ncbitaxon:",
    "ncbi:txid",
    "taxonomy:",
    "taxon:",
    "txid",
)
_PMCID_PREFIXES = (
    *_with_legacy_transport_aliases("https://www.ncbi.nlm.nih.gov/pmc/articles/"),
    *_with_legacy_transport_aliases("https://pmc.ncbi.nlm.nih.gov/articles/"),
    "pmcid:",
    "pmc:",
)
_MESH_PREFIXES = ("mesh id:", "mesh_id:", "mesh:")


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


def _normalize_openalex_candidate(candidate: str, *, prefix: str) -> str | None:
    normalized_prefix = prefix.upper()
    if not candidate.upper().startswith(normalized_prefix):
        return None
    suffix = candidate[len(normalized_prefix) :]
    return f"{normalized_prefix}{suffix}" if suffix.isdigit() else None


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
    id_normalizer: Callable[[object], object],
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
