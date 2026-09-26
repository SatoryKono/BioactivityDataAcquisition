"""Author extraction functions for CrossRef records.

Provides pure functions for extracting author details, ORCID identifiers,
and affiliations from CrossRef Works API responses.

These functions are:
- Stateless and pure (no side effects)
- Unit testable in isolation
- Reusable across different transformation contexts
"""

from __future__ import annotations

__all__ = ["extract_author_details", "extract_author_orcids"]


from bioetl.domain.types import JsonDict


def _strip_orcid_prefix(orcid: str) -> str:
    """Strip known ORCID URL prefixes while preserving unknown values."""
    prefixes = (
        *(f"{scheme}://orcid.org/" for scheme in ("https", "http")),
        *(f"{scheme}://ormolecule_id.org/" for scheme in ("https", "http")),
    )
    for prefix in prefixes:
        if orcid.startswith(prefix):
            return orcid[len(prefix) :]
    return orcid


def _is_orcid_identifier(orcid: str) -> bool:
    """Validate ORCID identifier layout."""
    return len(orcid) == 19 and orcid[4] == "-" and orcid[9] == "-" and orcid[14] == "-"


def _normalize_orcid(orcid_value: str | None) -> str | None:
    """Normalize ORCID to ID-only format (without URL prefix)."""
    if not isinstance(orcid_value, str):
        return None
    orcid = orcid_value.strip()
    if not orcid:
        return None
    orcid = _strip_orcid_prefix(orcid)
    if not _is_orcid_identifier(orcid):
        return None
    return orcid


def _extract_author_sequence(
    author: JsonDict,  # Any: raw Crossref API JSON
) -> str | None:
    """Extract and validate author sequence field."""
    sequence = author.get("sequence")
    if not sequence or not isinstance(sequence, str):
        return None
    sequence = sequence.strip().lower()
    return sequence if sequence in ("first", "additional") else None


def _extract_author_affiliations_list(
    author: JsonDict,  # Any: raw Crossref API JSON
) -> list[str]:
    """Extract affiliations list from author object."""
    affiliations: list[str] = []
    aff_list = author.get("affiliation", [])
    if not isinstance(aff_list, list):
        return affiliations
    for aff in aff_list:
        aff_name = aff.get("name") if isinstance(aff, dict) else aff
        if aff_name and isinstance(aff_name, str):
            aff_name = aff_name.strip()
            if aff_name:
                affiliations.append(aff_name)
    return affiliations


def _optional_stripped_text(value: object) -> str | None:
    """Return a stripped non-empty string, otherwise None."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _authenticated_orcid_flag(author: JsonDict) -> bool | None:  # Any: raw JSON
    """Read Crossref authenticated-ORCID flags as an optional bool."""
    authenticated = author.get("authenticated-orcid")
    if authenticated is None:
        authenticated = author.get("authenticated-ormolecule_id")
    if authenticated is None:
        return None
    return bool(authenticated)


def _build_author_detail(
    author: JsonDict,  # Any: raw Crossref API JSON
) -> JsonDict | None:  # Any: raw Crossref API JSON
    """Build author detail dict from raw author object."""
    given = _optional_stripped_text(author.get("given", ""))
    family = _optional_stripped_text(author.get("family", ""))
    org_name = _optional_stripped_text(author.get("name", ""))
    if not given and not family and not org_name:
        return None
    normalized_orcid = _normalize_orcid(author.get("ORCID"))
    authenticated = _authenticated_orcid_flag(author)
    return {
        "given": given,
        "family": family,
        "name": org_name,
        "orcid": normalized_orcid,
        # Compatibility alias expected by legacy tests/callers
        "ormolecule_id": normalized_orcid,
        "authenticated_orcid": authenticated,
        "authenticated_ormolecule_id": authenticated,
        "sequence": _extract_author_sequence(author),
        "affiliations": _extract_author_affiliations_list(author),
    }


def extract_author_details(
    publication: JsonDict,  # Any: raw Crossref API JSON
) -> list[JsonDict]:  # Any: raw Crossref API JSON
    """Extract full author details from CrossRef publication.

    Args:
        publication: CrossRef publication record.

    Returns:
        List of author detail dictionaries with keys:
        given, family, name, orcid, authenticated_orcid, sequence, affiliations.

    """
    author_details: list[
        JsonDict  # Any: raw Crossref API JSON
    ] = []
    for author in publication.get("author", []):
        if not isinstance(author, dict):
            continue
        detail = _build_author_detail(author)
        if detail:
            author_details.append(detail)
    return author_details


def extract_author_orcids(
    publication: JsonDict,  # Any: raw Crossref API JSON
) -> list[str]:
    """Extract list of ORCID identifiers from CrossRef publication.

    Extracts and normalizes all ORCID identifiers from the author array.
    Only includes non-empty, valid ORCIDs (normalized to ID-only format).

    Args:
        publication: CrossRef publication record.

    Returns:
        List of ORCID IDs (format: 0000-0000-0000-000X), preserving author order.
        Authors without ORCID are not included.

    """
    orcids: list[str] = []
    for author in publication.get("author", []):
        if not isinstance(author, dict):
            continue
        orcid = _normalize_orcid(author.get("ORCID"))
        if orcid:
            orcids.append(orcid)
    return orcids
