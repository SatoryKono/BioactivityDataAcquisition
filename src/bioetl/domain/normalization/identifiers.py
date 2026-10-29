"""Pure identifier normalization helpers."""

from __future__ import annotations

__all__ = [
    "ONTOLOGY_PREFIXES",
    "PMID_MAX_EXCLUSIVE",
    "get_ontology_prefix",
    "is_valid_ontology_id",
    "normalize_doi",
    "normalize_ontology_id",
    "normalize_ontology_id_strict",
    "normalize_pmid",
    "strip_doi_prefix",
]

_DOI_URL_PREFIXES = (
    *(f"{scheme}://doi.org/" for scheme in ("https", "http")),
    *(f"{scheme}://dx.doi.org/" for scheme in ("https", "http")),
    "doi:",
)
_PMID_URL_PREFIXES = (
    *(f"{scheme}://pubmed.ncbi.nlm.nih.gov/" for scheme in ("https", "http")),
    "pmid:",
)
_OBO_IRI_PREFIXES = (
    *(f"{scheme}://purl.obolibrary.org/obo/" for scheme in ("https", "http")),
)
PMID_MAX_EXCLUSIVE = 10_000_000_000


def strip_doi_prefix(doi: str) -> str:
    """Strip known DOI URL/scheme prefixes, preserving the DOI payload."""
    normalized = doi.strip()
    lowered = normalized.lower()
    for prefix in _DOI_URL_PREFIXES:
        if lowered.startswith(prefix):
            return normalized[len(prefix) :]
    return normalized


def normalize_doi(doi: str | None) -> str | None:
    """Normalize DOI to lowercase bare form."""
    if not doi:
        return None
    stripped = strip_doi_prefix(doi).strip().lower()
    return stripped if stripped else None


def _normalize_pmid_from_int(pmid: int) -> str | None:
    """Normalize integer PMID input."""
    return str(pmid) if 0 < pmid < PMID_MAX_EXCLUSIVE else None


def _normalize_pmid_from_str(pmid: str) -> str | None:
    """Normalize string PMID input."""
    value = pmid.strip()
    lowered = value.lower()
    for prefix in _PMID_URL_PREFIXES:
        if lowered.startswith(prefix):
            value = value[len(prefix) :]
            break
    value = value.strip().rstrip("/")
    if not value.isdigit():
        return None

    return _normalize_pmid_from_int(int(value))


def normalize_pmid(pmid: str | int | None) -> str | None:
    """Normalize PubMed ID to canonical digits-only string."""
    if pmid is None or isinstance(pmid, bool):
        return None

    if isinstance(pmid, int):
        return _normalize_pmid_from_int(pmid)

    if isinstance(pmid, str):
        return _normalize_pmid_from_str(pmid)


ONTOLOGY_PREFIXES = {
    "CLO": "CLO_",
    "EFO": "EFO_",
    "UBERON": "UBERON_",
    "BTO": "BTO_",
    "CALOHA": "TS-",
    "BAO": "BAO_",
    "GO": "GO_",
    "CHEBI": "CHEBI_",
    "CL": "CL_",
    "PR": "PR_",
    "SO": "SO_",
    "UO": "UO_",
}

_PREFIX_TO_CANONICAL = dict(ONTOLOGY_PREFIXES)
for p, c in list(_PREFIX_TO_CANONICAL.items()):
    canonical_prefix = c.rstrip("_")
    if canonical_prefix != p:
        _PREFIX_TO_CANONICAL[canonical_prefix] = c

_CANONICAL_PREFIXES = tuple(ONTOLOGY_PREFIXES.values())


def _fast_path_canonical(normalized: str, upper_val: str) -> str | None:
    if not upper_val.startswith(_CANONICAL_PREFIXES):
        return None
    for canonical in _CANONICAL_PREFIXES:
        if upper_val.startswith(canonical):
            return _fast_path_canonical_matched(normalized, canonical)
    return None


def _fast_path_canonical_matched(normalized: str, canonical: str) -> str:
    suffix = normalized[len(canonical) :]
    if canonical == ONTOLOGY_PREFIXES["CALOHA"] and suffix.upper().startswith("TS-"):
        return suffix.upper()
    return canonical + suffix


def _fast_path_colon(normalized: str) -> str | None:
    prefix, id_part = normalized.split(":", 1)
    prefix_upper = prefix.upper()
    canonical_prefix = _PREFIX_TO_CANONICAL.get(prefix_upper)
    if not canonical_prefix:
        return None
    if prefix_upper == "CALOHA":
        id_part_upper = id_part.upper()
        if id_part_upper.startswith("TS-"):
            return id_part_upper
    return f"{canonical_prefix}{id_part}"


def _fast_path_underscore(normalized: str) -> str | None:
    prefix, suffix = normalized.split("_", 1)
    prefix_upper = prefix.upper()
    canonical_prefix = _PREFIX_TO_CANONICAL.get(prefix_upper)
    if not canonical_prefix:
        return None
    if prefix_upper == "CALOHA" and suffix.upper().startswith("TS-"):
        return suffix.upper()
    return f"{canonical_prefix}{suffix}"


def _fast_path_space(normalized: str) -> str | None:
    parts = normalized.split()
    if len(parts) == 2:
        canonical_prefix = _PREFIX_TO_CANONICAL.get(parts[0].upper())
        if canonical_prefix:
            return f"{canonical_prefix}{parts[1].zfill(7)}"
    return None


def _check_obo_iri(normalized: str) -> str | None:
    lowered = normalized.lower()
    for prefix in _OBO_IRI_PREFIXES:
        if lowered.startswith(prefix):
            return normalize_ontology_id(normalized[len(prefix) :])
    return None


def normalize_ontology_id(value: str) -> str | None:
    """Canonicalize ontology IDs with consistent prefix format."""
    if type(value) is not str:
        return None
    from bioetl.domain.normalization.text import normalize_string

    normalized = normalize_string(value)
    if normalized is None:
        return "" if value == "" else None

    # 1. Very fast path: already canonical or correct prefix format
    canonical_match = _fast_path_canonical(normalized, normalized.upper())
    if canonical_match is not None:
        return canonical_match

    return _fallback_normalize_ontology_id(normalized)


def _fallback_normalize_ontology_id(normalized: str) -> str | None:
    # Quick exclusion
    if not (
        ":" in normalized or " " in normalized or "_" in normalized or "/" in normalized
    ):
        return normalized

    return _process_slow_paths(normalized)


def _process_slow_paths(normalized: str) -> str | None:
    obo_match = _check_obo_iri(normalized)
    if obo_match is not None:
        return obo_match

    if ":" in normalized:
        colon_match = _fast_path_colon(normalized)
        if colon_match is not None:
            return colon_match

    return _process_slow_paths_fallback(normalized)


def _process_slow_paths_fallback(normalized: str) -> str | None:
    if "_" in normalized:
        underscore_match = _fast_path_underscore(normalized)
        if underscore_match is not None:
            return underscore_match

    if " " in normalized:
        space_match = _fast_path_space(normalized)
        if space_match is not None:
            return space_match

    return normalized


def normalize_ontology_id_strict(value: str) -> str | None:
    """Normalize ontology IDs while rejecting unknown prefixes."""
    result = normalize_ontology_id(value)
    if result is None:
        return None

    for prefix in ONTOLOGY_PREFIXES.values():
        if result.startswith(prefix):
            return result
    return None


def _get_prefix_from_canonical(id_value: str) -> str | None:
    """Extract prefix from canonical underscore format."""
    for prefix, canonical in ONTOLOGY_PREFIXES.items():
        if id_value.startswith(canonical):
            return prefix
    return None


def _get_prefix_from_colon(id_value: str) -> str | None:
    """Extract prefix from colon format."""
    if ":" in id_value:
        prefix = id_value.split(":")[0].upper()
        if prefix in ONTOLOGY_PREFIXES:
            return prefix
    return None


def get_ontology_prefix(id_value: object) -> str | None:
    """Extract ontology prefix from an ID string."""
    if not isinstance(id_value, str):
        return None

    return _get_prefix_from_canonical(id_value) or _get_prefix_from_colon(id_value)


def is_valid_ontology_id(id_value: object) -> bool:
    """Check whether a string is a valid ontology ID."""
    if id_value is None or not isinstance(id_value, str):
        return False

    return get_ontology_prefix(id_value) is not None
