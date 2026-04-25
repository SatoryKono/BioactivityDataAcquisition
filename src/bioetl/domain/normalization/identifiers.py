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
    "normalize_pmc_id",
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

    return None


def normalize_pmc_id(pmc_id: str | None) -> str | None:
    """Normalize PMC ID to uppercase with ``PMC`` prefix."""
    if not pmc_id:
        return None
    stripped = pmc_id.strip()
    if not stripped:
        return None
    if not stripped.upper().startswith("PMC"):
        return f"PMC{stripped}"
    return stripped.upper()


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
}


def _normalize_colon_format(value: str) -> str | None:
    """Handle colon format ontology IDs (CLO:1234 -> CLO_1234)."""
    if ":" in value:
        prefix, id_part = value.split(":", 1)
        prefix = prefix.upper()
        if prefix in ONTOLOGY_PREFIXES:
            if prefix == "CALOHA":
                normalized_id_part = id_part.upper()
                if normalized_id_part.startswith("TS-"):
                    return normalized_id_part
            return f"{ONTOLOGY_PREFIXES[prefix]}{id_part}"
    return None


def _get_underscore_suffix(
    value: str, prefix: str, canonical_prefix: str, upper_value: str
) -> str | None:
    upper_canonical = canonical_prefix.upper()
    if upper_value.startswith(upper_canonical):
        return value[len(upper_canonical) :]

    underscore_prefix = f"{prefix}_"
    if upper_value.startswith(underscore_prefix):
        suffix = value[len(underscore_prefix) :]
        if prefix == "CALOHA" and suffix.upper().startswith("TS-"):
            return suffix.upper()
        return suffix
    return None


def _normalize_underscore_format(value: str) -> str | None:
    """Handle underscore format ontology IDs (already correct format)."""
    upper_value = value.upper()
    for prefix, canonical_prefix in ONTOLOGY_PREFIXES.items():
        suffix = _get_underscore_suffix(value, prefix, canonical_prefix, upper_value)
        if suffix is not None:
            if prefix == "CALOHA" and suffix.upper().startswith("TS-"):
                return suffix.upper()
            return f"{canonical_prefix}{suffix}"
    return None


def _normalize_space_format(value: str) -> str | None:
    """Handle space format ontology IDs (UBERON 7 -> UBERON_0000007)."""
    parts = value.split()
    if len(parts) == 2 and parts[0].upper() in ONTOLOGY_PREFIXES:
        prefix = ONTOLOGY_PREFIXES[parts[0].upper()]
        id_part = parts[1].zfill(7)
        return f"{prefix}{id_part}"
    return None


def _normalize_obo_iri_format(value: str) -> str | None:
    """Handle OBO IRIs such as purl.obolibrary.org/obo/GO_0008150."""
    lowered = value.lower()
    for prefix in _OBO_IRI_PREFIXES:
        if lowered.startswith(prefix):
            return _apply_normalization_strategies(value[len(prefix) :])
    return None


def _validate_input(value: str) -> str | None:
    """Validate and preprocess input value."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    from bioetl.domain.normalization.text import normalize_string

    normalized = normalize_string(value)
    if normalized is not None:
        return normalized
    if value == "":
        return ""
    return None


def _apply_normalization_strategies(normalized: str) -> str:
    """Apply normalization strategies in priority order."""
    strategies = [
        _normalize_obo_iri_format,
        _normalize_colon_format,
        _normalize_underscore_format,
        _normalize_space_format,
    ]

    for strategy in strategies:
        result = strategy(normalized)
        if result is not None:
            return result

    return normalized


def normalize_ontology_id(value: str) -> str | None:
    """Canonicalize ontology IDs with consistent prefix format."""
    normalized = _validate_input(value)
    if normalized is None:
        return None

    return _apply_normalization_strategies(normalized)


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


def get_ontology_prefix(id_value: str) -> str | None:
    """Extract ontology prefix from an ID string."""
    if id_value is None:
        return None

    return _get_prefix_from_canonical(id_value) or _get_prefix_from_colon(id_value)


def is_valid_ontology_id(id_value: str) -> bool:
    """Check whether a string is a valid ontology ID."""
    if id_value is None or not isinstance(id_value, str):
        return False

    return get_ontology_prefix(id_value) is not None
