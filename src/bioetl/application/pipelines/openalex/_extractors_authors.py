"""Author and institution extractors for OpenAlex records."""

from __future__ import annotations

from bioetl.application.pipelines.openalex._extractors_common import (
    _extract_id_from_url,
    _extract_orcid_from_url,
)
from bioetl.domain.types import JsonDict


def extract_authors(
    authorships: list[JsonDict],  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract author display names from authorships array.

    Args:
        authorships: List of authorship dicts from the OpenAlex API response.

    Returns:
        List of author display names in authorship order.
    """
    authors: list[str] = []
    for authorship in authorships:
        author = authorship.get("author", {})
        if not isinstance(author, dict):
            continue
        name = author.get("display_name")
        if name and isinstance(name, str):
            authors.append(name.strip())
    return authors


def extract_author_ids(
    authorships: list[JsonDict],  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract OpenAlex author IDs from authorships preserving order.

    Args:
        authorships: List of authorship dicts from the OpenAlex API response.

    Returns:
        List of extracted author ID strings (empty string for missing IDs).
    """
    author_ids: list[str] = []
    for authorship in authorships:
        author = authorship.get("author", {})
        if not isinstance(author, dict):
            author_ids.append("")
            continue
        raw_id = author.get("id")
        extracted = _extract_id_from_url(raw_id)
        author_ids.append(extracted or "")
    return author_ids


def extract_author_orcids(
    authorships: list[JsonDict],  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract ORCID identifiers from authorships preserving order.

    Args:
        authorships: List of authorship dicts from the OpenAlex API response.

    Returns:
        List of ORCID identifier strings (empty string for missing ORCIDs).
    """
    orcids: list[str] = []
    for authorship in authorships:
        author = authorship.get("author", {})
        if not isinstance(author, dict):
            orcids.append("")
            continue
        orcid_url = author.get("orcid")
        if orcid_url is None:
            orcid_url = author.get("ormolecule_id")
        orcids.append(_extract_orcid_from_url(orcid_url))
    return orcids


def extract_affiliations(
    authorships: list[JsonDict],  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract unique affiliations from authorships (sorted).

    Args:
        authorships: List of authorship dicts from the OpenAlex API response.

    Returns:
        Sorted list of unique institution display names.
    """
    affiliations: set[str] = set()
    for authorship in authorships:
        institutions = authorship.get("institutions", [])
        if not isinstance(institutions, list):
            continue
        for inst in institutions:
            if not isinstance(inst, dict):
                continue
            name = inst.get("display_name")
            if name and isinstance(name, str):
                affiliations.add(name.strip())

    return sorted(affiliations)


def extract_institution_ids(
    authorships: list[JsonDict],  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract unique OpenAlex institution IDs from authorships.

    Args:
        authorships: List of authorship dicts from the OpenAlex API response.

    Returns:
        Sorted list of unique institution ID strings.
    """
    ids: set[str] = set()
    for authorship in authorships:
        institutions = authorship.get("institutions", [])
        if not isinstance(institutions, list):
            continue
        for inst in institutions:
            if not isinstance(inst, dict):
                continue
            raw_id = inst.get("id")
            extracted = _extract_id_from_url(raw_id)
            if extracted:
                ids.add(extracted)
    return sorted(ids)


def extract_institution_country_codes(
    authorships: list[JsonDict],  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract unique institution country codes from authorships.

    Args:
        authorships: List of authorship dicts from the OpenAlex API response.

    Returns:
        Sorted list of unique uppercased country code strings.
    """
    codes: set[str] = set()
    for authorship in authorships:
        institutions = authorship.get("institutions", [])
        if not isinstance(institutions, list):
            continue
        for inst in institutions:
            if not isinstance(inst, dict):
                continue
            code = inst.get("country_code")
            if code and isinstance(code, str):
                codes.add(code.upper())
    return sorted(codes)


def extract_institution_ror_ids(
    authorships: list[JsonDict],  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract unique ROR IDs from authorships institutions.

    Args:
        authorships: List of authorship dicts from the OpenAlex API response.

    Returns:
        Sorted list of unique ROR ID URLs (https://ror.org/...).
    """
    ror_ids: set[str] = set()
    for authorship in authorships:
        institutions = authorship.get("institutions", [])
        if not isinstance(institutions, list):
            continue
        for inst in institutions:
            if not isinstance(inst, dict):
                continue
            ror = inst.get("ror")
            if ror and isinstance(ror, str) and ror.startswith("https://ror.org/"):
                ror_ids.add(ror)
    return sorted(ror_ids)


__all__ = [
    "extract_affiliations",
    "extract_author_ids",
    "extract_author_orcids",
    "extract_authors",
    "extract_institution_country_codes",
    "extract_institution_ids",
    "extract_institution_ror_ids",
]
