"""Publication-level field extractors for OpenAlex records."""

from __future__ import annotations

from bioetl.application.pipelines.openalex._extractors_common import (
    _extract_id_from_url,
)
from bioetl.domain.normalization import strip_doi_prefix
from bioetl.domain.types import JsonDict


def extract_doi(doi_url: str | None) -> str | None:
    """Extract bare DOI from OpenAlex DOI URL.

    Args:
        doi_url: DOI URL string (e.g. ``"https://doi.org/10.1234/example"``), or None.

    Returns:
        Bare DOI string without URL prefix, or None if input is empty.
    """
    if not doi_url:
        return None
    return strip_doi_prefix(doi_url)


def extract_openalex_id(openalex_url: str | None) -> str | None:
    """Extract OpenAlex ID from OpenAlex URL.

    Args:
        openalex_url: OpenAlex entity URL string (e.g. ``"https://openalex.org/W12345"``),
            or None.

    Returns:
        Last path segment of the URL as ID string, or None if input is empty.
    """
    if not openalex_url:
        return None
    if "/" in openalex_url:
        return openalex_url.split("/")[-1]
    return openalex_url


def extract_journal_info(
    primary_location: (
        JsonDict | None  # Any: untyped API JSON record
    ),  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict:  # Any: untyped JSON fragment from OpenAlex API
    """Extract journal info (journal, issn, publisher) from primary_location.

    Args:
        primary_location: OpenAlex primary_location dict from the API response, or None.

    Returns:
        Dictionary with journal, issn, and publisher keys (None values if unavailable).
    """
    if not primary_location or not isinstance(primary_location, dict):
        return {"journal": None, "issn": None, "publisher": None}

    source = primary_location.get("source", {}) or {}
    if not isinstance(source, dict):
        return {"journal": None, "issn": None, "publisher": None}

    return {
        "journal": source.get("display_name"),
        "issn": source.get("issn_l"),
        "publisher": source.get("host_organization_name"),
    }


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Reconstruct abstract from OpenAlex inverted index format.

    Args:
        inverted_index: Mapping of word to list of integer word positions, or None.

    Returns:
        Reconstructed abstract text with words in position order, or None if empty.
    """
    if not inverted_index or not isinstance(inverted_index, dict):
        return None

    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int):
                word_positions.append((pos, word))

    if not word_positions:
        return None

    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def extract_open_access_info(
    open_access: JsonDict | None,  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict:  # Any: untyped JSON fragment from OpenAlex API
    """Extract Open Access info (is_oa, oa_status).

    Args:
        open_access: OpenAlex open_access dict from the API response, or None.

    Returns:
        Dictionary with is_oa and oa_status keys (None values if unavailable).
    """
    if not open_access or not isinstance(open_access, dict):
        return {"is_oa": None, "oa_status": None}

    return {
        "is_oa": open_access.get("is_oa"),
        "oa_status": open_access.get("oa_status"),
    }


def extract_external_ids(
    ids: JsonDict | None,  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict:  # Any: untyped JSON fragment from OpenAlex API
    """Extract external identifiers (pmid, pmcid, mag_id) from ids object.

    Args:
        ids: OpenAlex ids dict from the API response, or None.

    Returns:
        Dictionary with pmid, pmmolecule_id, and mag_id keys (None if unavailable).
    """
    if not ids or not isinstance(ids, dict):
        return {"pmid": None, "pmmolecule_id": None, "mag_id": None}

    from bioetl.domain.value_objects.publications import PubMedId

    raw_pmid = _extract_id_from_url(ids.get("pmid"))
    pmid_vo = PubMedId.from_raw(raw_pmid)

    pmcid = _extract_id_from_url(ids.get("pmcid") or ids.get("pmmolecule_id"))

    mag_raw = ids.get("mag")

    return {
        "pmid": str(pmid_vo) if pmid_vo else None,
        "pmmolecule_id": pmcid,
        "mag_id": str(mag_raw) if mag_raw is not None else None,
    }


def extract_mesh_terms(
    mesh: list[JsonDict] | None,  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract unique MeSH descriptor names from mesh array.

    Args:
        mesh: List of MeSH term dicts from the OpenAlex API response, or None.

    Returns:
        Ordered list of unique MeSH descriptor name strings.
    """
    if not mesh or not isinstance(mesh, list):
        return []

    seen: set[str] = set()
    result: list[str] = []

    for term in mesh:
        if not isinstance(term, dict):
            continue
        name = term.get("descriptor_name")
        if name and isinstance(name, str) and name not in seen:
            seen.add(name)
            result.append(name)

    return result


def extract_keywords(
    keywords: (
        list[JsonDict] | None  # Any: untyped API JSON record
    ),  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract keyword display names from keywords array.

    Args:
        keywords: List of keyword dicts from the OpenAlex API response, or None.

    Returns:
        List of stripped keyword display name strings.
    """
    if not keywords or not isinstance(keywords, list):
        return []

    result: list[str] = []
    for kw in keywords:
        if not isinstance(kw, dict):
            continue
        name = kw.get("display_name")
        if name and isinstance(name, str):
            result.append(name.strip())

    return result


def extract_biblio_info(
    biblio: JsonDict | None,  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict:  # Any: untyped JSON fragment from OpenAlex API
    """Extract bibliographic info (volume, issue, page_first, page_last).

    Args:
        biblio: OpenAlex biblio dict from the API response, or None.

    Returns:
        Dictionary with volume, issue, page_first, and page_last keys.
    """
    if not biblio or not isinstance(biblio, dict):
        return {
            "volume": None,
            "issue": None,
            "page_first": None,
            "page_last": None,
        }
    return {
        "volume": biblio.get("volume"),
        "issue": biblio.get("issue"),
        "page_first": biblio.get("first_page"),
        "page_last": biblio.get("last_page"),
    }


__all__ = [
    "extract_biblio_info",
    "extract_doi",
    "extract_external_ids",
    "extract_journal_info",
    "extract_keywords",
    "extract_mesh_terms",
    "extract_open_access_info",
    "extract_openalex_id",
    "reconstruct_abstract",
]
