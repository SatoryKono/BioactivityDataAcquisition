"""Field extraction functions for OpenAlex records.

Pure functions for extracting/normalizing fields from OpenAlex API responses.
"""

from __future__ import annotations

import re
from typing import Any
from bioetl.domain.types import JsonDict

# ORCID format: NNNN-NNNN-NNNN-NNNN (last char can be X for checksum)
_ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")

__all__ = [
    "extract_affiliations",
    "extract_author_ids",
    "extract_author_orcids",
    "extract_authors",
    "extract_biblio_info",
    "extract_doi",
    "extract_external_ids",
    "extract_grants",
    "extract_institution_country_codes",
    "extract_institution_ids",
    "extract_institution_ror_ids",
    "extract_journal_info",
    "extract_keywords",
    "extract_mesh_terms",
    "extract_open_access_info",
    "extract_openalex_id",
    "extract_primary_topic",
    "extract_topics",
    "reconstruct_abstract",
]


def _extract_id_from_url(url: str | None) -> str | None:
    """Extract ID from OpenAlex URL (helper function).

    Args:
        url: URL or bare ID string.

    Returns:
        Extracted ID or original value.
    """
    if not url or not isinstance(url, str):
        return None
    return url.rstrip("/").split("/")[-1] if "/" in url else url


def _get_nested_display_name(
    obj: Any,  # Any: untyped JSON fragment from OpenAlex API
) -> str | None:
    """Get display_name from nested dict (helper function).

    Args:
        obj: Nested object (dict expected).

    Returns:
        display_name string or None.
    """
    if isinstance(obj, dict):
        return obj.get("display_name")
    return None


def _parse_topic_dict(
    topic: JsonDict,  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict | None:  # Any: untyped JSON fragment from OpenAlex API
    """Parse a single topic dict into normalized format (helper function).

    Args:
        topic: Raw topic dict from OpenAlex API.

    Returns:
        Normalized topic dict or None if invalid.
    """
    display_name = topic.get("display_name")
    if not display_name or not isinstance(display_name, str):
        return None

    score = topic.get("score")
    score_val = float(score) if isinstance(score, (int, float)) else 0.0

    return {
        "id": _extract_id_from_url(topic.get("id")),
        "display_name": display_name.strip(),
        "score": score_val,
        "subfield": _get_nested_display_name(topic.get("subfield") or {}),
        "field": _get_nested_display_name(topic.get("field") or {}),
        "domain": _get_nested_display_name(topic.get("domain") or {}),
    }


def extract_doi(doi_url: str | None) -> str | None:
    """Extract bare DOI from OpenAlex DOI URL.

    Args:
        doi_url: Doi url.

    Returns:
        Extracted value.
    """
    if not doi_url:
        return None
    if doi_url.startswith("https://doi.org/"):
        return doi_url[16:]
    if doi_url.startswith("http://doi.org/"):
        return doi_url[15:]
    if doi_url.startswith("doi:"):
        return doi_url[4:]
    return doi_url


def extract_openalex_id(openalex_url: str | None) -> str | None:
    """Extract OpenAlex ID from OpenAlex URL.

    Args:
        openalex_url: Openalex url.

    Returns:
        Extracted value.
    """
    if not openalex_url:
        return None
    if "/" in openalex_url:
        return openalex_url.split("/")[-1]
    return openalex_url


def extract_authors(
    authorships: list[JsonDict],  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract author display names from authorships array.

    Args:
        authorships: Authorships.

    Returns:
        Extracted value.
    """
    authors = []
    for authorship in authorships:
        author = authorship.get("author", {})
        if not isinstance(author, dict):
            continue
        name = author.get("display_name")
        if name and isinstance(name, str):
            authors.append(name.strip())
    return authors


def _extract_orcid_from_url(url: str | None) -> str:
    """Extract and validate ORCID from URL (helper function).

    Args:
        url: ORCID URL (e.g., "https://orcid.org/0000-0001-2345-6789") or None.

    Returns:
        Extracted ORCID ID if valid, empty string otherwise.
    """
    if not url or not isinstance(url, str):
        return ""

    # Accept raw ORCID or ORCID URL variants (including legacy typo domain)
    orcid = url.strip().rstrip("/")
    if "/" in orcid:
        orcid = orcid.split("/")[-1]

    # Validate format
    if _ORCID_PATTERN.match(orcid):
        return orcid

    return ""


def extract_author_ids(
    authorships: list[JsonDict],  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract OpenAlex author IDs from authorships (preserving order).

    Args:
        authorships: List of authorship dicts from OpenAlex API.

    Returns:
        List of OpenAlex author IDs (e.g., ["A1234567890", "", "A9876543210"]).
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
    """Extract ORCID identifiers from authorships (preserving order).

    Args:
        authorships: List of authorship dicts from OpenAlex API.

    Returns:
        List of ORCID IDs (empty string for missing), same length as input.

    Example:
        >>> extract_author_orcids([
        ...     {"author": {"orcid": "https://orcid.org/0000-0001-2345-6789"}},
        ...     {"author": {"orcid": None}},
        ... ])
        ['0000-0001-2345-6789', '']
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
        authorships: Authorships.

    Returns:
        Extracted value.
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
        authorships: List of authorship dicts from OpenAlex API.

    Returns:
        Sorted list of unique institution IDs (e.g., ["I1234567890", "I9876543210"]).

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
        authorships: List of authorship dicts from OpenAlex API.

    Returns:
        Sorted list of unique ISO 2-letter country codes (e.g., ["DE", "GB", "US"]).

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
        authorships: List of authorship dicts from OpenAlex API.

    Returns:
        Sorted list of unique ROR IDs (full URL format).
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


def extract_topics(
    topics: list[JsonDict] | None,  # Any: untyped JSON fragment from OpenAlex API
    max_count: int = 10,
) -> list[JsonDict]:  # Any: untyped JSON fragment from OpenAlex API
    """Extract topics with hierarchical classification (domain/field/subfield/topic).

    Args:
        topics: Topics.
        max_count: Number of max.

    Returns:
        Extracted value.
    """
    if not topics or not isinstance(topics, list):
        return []

    result: list[JsonDict] = []  # Any: untyped JSON fragment from OpenAlex API
    for topic in topics[:max_count]:
        if not isinstance(topic, dict):
            continue
        parsed = _parse_topic_dict(topic)
        if parsed:
            result.append(parsed)

    return result


def extract_primary_topic(
    primary_topic: JsonDict  # Any: untyped API JSON record
    | None,  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict | None:  # Any: untyped JSON fragment from OpenAlex API
    """Extract single most relevant topic for a work.

    Args:
        primary_topic: Primary topic.

    Returns:
        Extracted value.
    """
    if not primary_topic or not isinstance(primary_topic, dict):
        return None
    return _parse_topic_dict(primary_topic)


def _parse_grant_dict(
    grant: JsonDict,  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict | None:  # Any: untyped JSON fragment from OpenAlex API
    """Parse a single grant dict into normalized format (helper function).

    Args:
        grant: Raw grant dict from OpenAlex API.

    Returns:
        Normalized grant dict or None if invalid.
    """
    funder_name = grant.get("funder_display_name")
    if not funder_name or not isinstance(funder_name, str):
        return None

    award_id = grant.get("award_id")
    award_str = str(award_id).strip() if award_id else None

    return {
        "funder": _extract_id_from_url(grant.get("funder")),
        "funder_display_name": funder_name.strip(),
        "award_id": award_str,
    }


def extract_grants(
    grants: list[JsonDict] | None,  # Any: untyped JSON fragment from OpenAlex API
) -> list[JsonDict]:  # Any: untyped JSON fragment from OpenAlex API
    """Extract grant/funding information from grants array.

    Args:
        grants: Grants.

    Returns:
        Extracted value.
    """
    if not grants or not isinstance(grants, list):
        return []

    result: list[JsonDict] = []  # Any: untyped JSON fragment from OpenAlex API
    for grant in grants:
        if not isinstance(grant, dict):
            continue
        parsed = _parse_grant_dict(grant)
        if parsed:
            result.append(parsed)

    return result


def extract_journal_info(
    primary_location: JsonDict  # Any: untyped API JSON record
    | None,  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict:  # Any: untyped JSON fragment from OpenAlex API
    """Extract journal info (journal, issn, publisher) from primary_location.

    Args:
        primary_location: Primary location.

    Returns:
        Extracted value.
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
        inverted_index: Inverted index.

    Returns:
        The str | None result.
    """
    if not inverted_index or not isinstance(inverted_index, dict):
        return None

    # Build position -> word mapping
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int):
                word_positions.append((pos, word))

    if not word_positions:
        return None

    # Sort by position and join
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def extract_open_access_info(
    open_access: JsonDict | None,  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict:  # Any: untyped JSON fragment from OpenAlex API
    """Extract Open Access info (is_oa, oa_status).

    Args:
        open_access: Open access.

    Returns:
        Extracted value.
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
        ids: Ids.

    Returns:
        Extracted value.
    """
    if not ids or not isinstance(ids, dict):
        return {"pmid": None, "pmmolecule_id": None, "mag_id": None}

    from bioetl.domain.value_objects.publications import PubMedId

    # PMID: normalize via PubMedId VO (strips leading zeros, validates bounds)
    raw_pmid = _extract_id_from_url(ids.get("pmid"))
    pmid_vo = PubMedId.from_raw(raw_pmid)

    # PMCID/legacy pmmolecule_id: extract from URL (e.g. .../PMC123456)
    pmcid = _extract_id_from_url(ids.get("pmcid") or ids.get("pmmolecule_id"))

    # MAG ID (can be int or string)
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
        mesh: Mesh.

    Returns:
        Extracted value.
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
    keywords: list[JsonDict]  # Any: untyped API JSON record
    | None,  # Any: untyped JSON fragment from OpenAlex API
) -> list[str]:
    """Extract keyword display names from keywords array.

    Args:
        keywords: Keywords.

    Returns:
        Extracted value.
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
        biblio: Biblio.

    Returns:
        Extracted value.
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
