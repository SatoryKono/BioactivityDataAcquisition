"""Pure identifier normalization helpers."""

from __future__ import annotations

__all__ = [
    "PMID_MAX_EXCLUSIVE",
    "normalize_doi",
    "normalize_pmc_id",
    "normalize_pmid",
    "strip_doi_prefix",
    "normalize_ontology_id",
    "normalize_ontology_id_strict",
    "get_ontology_prefix",
    "is_valid_ontology_id",
    "ONTOLOGY_PREFIXES",
]

_DOI_URL_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "doi:",
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


# ============================================================================
# Ontology Identifier Normalization
# ============================================================================


# Standard ontology prefixes and their canonical formats
ONTOLOGY_PREFIXES = {
    "CLO": "CLO_",  # Cell Line Ontology
    "EFO": "EFO_",  # Experimental Factor Ontology
    "UBERON": "UBERON_",  # Uber Anatomical Ontology
    "BAO": "BAO_",  # BioAssay Ontology
    "GO": "GO_",  # Gene Ontology
    "CHEBI": "CHEBI_",  # Chemical Entities of Biological Interest
    "CL": "CL_",  # Cell Ontology
    "PR": "PR_",  # Protein Ontology
    "SO": "SO_",  # Sequence Ontology
}


def normalize_ontology_id(value: str) -> str | None:
    """Canonicalize ontology IDs with consistent prefix format.
    
    This function normalizes various ontology ID formats to a consistent
    underscore-separated format. It handles colon format, underscore format,
    and space format inputs.
    
    Args:
        value: The ontology ID to normalize
        
    Returns:
        Normalized ontology ID or None if invalid
        
    Examples:
        >>> normalize_ontology_id("CLO:0000034")
        "CLO_0000034"
        >>> normalize_ontology_id("EFO_0000087")
        "EFO_0000087"
        >>> normalize_ontology_id("UBERON 7")
        "UBERON_0000007"
        >>> normalize_ontology_id("unknown")
        "unknown"
    """
    if value is None:
        return None
    
    if not isinstance(value, str):
        return None
    
    # Normalize string first (trim whitespace, etc.)
    from bioetl.domain.normalization.text import normalize_string
    normalized = normalize_string(value)
    if normalized is None:
        return None
    
    # Handle colon format (CLO:1234 -> CLO_1234)
    if ":" in normalized:
        prefix, id_part = normalized.split(":", 1)
        prefix = prefix.upper()
        if prefix in ONTOLOGY_PREFIXES:
            return f"{ONTOLOGY_PREFIXES[prefix]}{id_part}"
        return normalized  # Unknown prefix, return as-is
    
    # Handle underscore format (already correct)
    for prefix in ONTOLOGY_PREFIXES.values():
        if normalized.startswith(prefix):
            return normalized
    
    # Handle space format (UBERON 7 -> UBERON_0000007)
    parts = normalized.split()
    if len(parts) == 2 and parts[0].upper() in ONTOLOGY_PREFIXES:
        prefix = ONTOLOGY_PREFIXES[parts[0].upper()]
        id_part = parts[1].zfill(7)  # Pad to 7 digits
        return f"{prefix}{id_part}"
    
    # Unknown format, return as-is
    return normalized


def normalize_ontology_id_strict(value: str) -> str | None:
    """Strict ontology ID normalization that only accepts known prefixes.
    
    Unlike normalize_ontology_id, this function returns None for unknown
    ontology prefixes, ensuring only valid ontology IDs pass through.
    
    Args:
        value: The ontology ID to normalize
        
    Returns:
        Normalized ontology ID or None if invalid or unknown prefix
        
    Examples:
        >>> normalize_ontology_id_strict("CLO:0000034")
        "CLO_0000034"
        >>> normalize_ontology_id_strict("UNKNOWN:123")
        None
    """
    result = normalize_ontology_id(value)
    if result is None:
        return None
    
    # Check if result starts with known prefix
    for prefix in ONTOLOGY_PREFIXES.values():
        if result.startswith(prefix):
            return result
    
    # Unknown prefix
    return None


def get_ontology_prefix(id_value: str) -> str | None:
    """Extract ontology prefix from an ID string.
    
    Args:
        id_value: The ontology ID
        
    Returns:
        Ontology prefix if recognized, None otherwise
        
    Examples:
        >>> get_ontology_prefix("CLO_0000034")
        "CLO"
        >>> get_ontology_prefix("unknown")
        None
    """
    if id_value is None:
        return None
    
    for prefix, canonical in ONTOLOGY_PREFIXES.items():
        if id_value.startswith(canonical):
            return prefix
    
    # Check colon format
    if ":" in id_value:
        prefix = id_value.split(":")[0].upper()
        if prefix in ONTOLOGY_PREFIXES:
            return prefix
    
    return None


def is_valid_ontology_id(id_value: str) -> bool:
    """Check if a string is a valid ontology ID.
    
    Args:
        id_value: The string to check
        
    Returns:
        True if valid ontology ID, False otherwise
        
    Examples:
        >>> is_valid_ontology_id("CLO_0000034")
        True
        >>> is_valid_ontology_id("unknown")
        False
    """
    if id_value is None or not isinstance(id_value, str):
        return False
    
    return get_ontology_prefix(id_value) is not None
