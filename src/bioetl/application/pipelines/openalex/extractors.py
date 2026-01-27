"""Field extraction functions for OpenAlex records.

Pure functions for extracting/normalizing fields from OpenAlex API responses.
Topics vs Concepts: OpenAlex deprecated concepts in 2024; use topics instead.
"""

from __future__ import annotations

import warnings
from typing import Any


def _extract_id_from_url(url: str | None) -> str | None:
    """Extract ID from OpenAlex URL (helper function).

    Args:
        url: URL or bare ID string.

    Returns:
        Extracted ID or original value.
    """
    if not url or not isinstance(url, str):
        return None
    return url.split("/")[-1] if "/" in url else url


def _get_nested_display_name(obj: Any) -> str | None:
    """Get display_name from nested dict (helper function).

    Args:
        obj: Nested object (dict expected).

    Returns:
        display_name string or None.
    """
    if isinstance(obj, dict):
        return obj.get("display_name")
    return None


def _parse_topic_dict(topic: dict[str, Any]) -> dict[str, Any] | None:
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
    """Extract bare DOI from OpenAlex DOI URL."""
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
    """Extract OpenAlex ID from OpenAlex URL."""
    if not openalex_url:
        return None
    if "/" in openalex_url:
        return openalex_url.split("/")[-1]
    return openalex_url


def extract_authors(authorships: list[dict[str, Any]]) -> list[str]:
    """Extract author display names from authorships array."""
    authors = []
    for authorship in authorships:
        author = authorship.get("author", {})
        if not isinstance(author, dict):
            continue
        name = author.get("display_name")
        if name and isinstance(name, str):
            authors.append(name.strip())
    return authors


def extract_affiliations(authorships: list[dict[str, Any]]) -> list[str]:
    """Extract unique affiliations from authorships (sorted)."""
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


def extract_institution_ids(authorships: list[dict[str, Any]]) -> list[str]:
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


def extract_institution_country_codes(authorships: list[dict[str, Any]]) -> list[str]:
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


def extract_concepts(
    concepts: list[dict[str, Any]],
    max_count: int = 10,
    *,
    warn_deprecated: bool = False,
) -> list[str]:
    """Extract top concept names (DEPRECATED: use extract_topics instead)."""
    if warn_deprecated:
        warnings.warn(
            "extract_concepts() is deprecated. OpenAlex deprecated the 'concepts' "
            "field in 2024 in favor of 'topics'. Use extract_topics() and "
            "extract_primary_topic() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
    result = []
    for concept in concepts[:max_count]:
        if not isinstance(concept, dict):
            continue
        name = concept.get("display_name")
        if name and isinstance(name, str):
            result.append(name.strip())
    return result


def extract_topics(
    topics: list[dict[str, Any]] | None,
    max_count: int = 10,
) -> list[dict[str, Any]]:
    """Extract topics with hierarchical classification (domain/field/subfield/topic)."""
    if not topics or not isinstance(topics, list):
        return []

    result: list[dict[str, Any]] = []
    for topic in topics[:max_count]:
        if not isinstance(topic, dict):
            continue
        parsed = _parse_topic_dict(topic)
        if parsed:
            result.append(parsed)

    return result


def extract_primary_topic(
    primary_topic: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Extract single most relevant topic for a work."""
    if not primary_topic or not isinstance(primary_topic, dict):
        return None
    return _parse_topic_dict(primary_topic)


def _parse_grant_dict(grant: dict[str, Any]) -> dict[str, Any] | None:
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


def extract_grants(grants: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Extract grant/funding information from grants array."""
    if not grants or not isinstance(grants, list):
        return []

    result: list[dict[str, Any]] = []
    for grant in grants:
        if not isinstance(grant, dict):
            continue
        parsed = _parse_grant_dict(grant)
        if parsed:
            result.append(parsed)

    return result


def extract_journal_info(primary_location: dict[str, Any] | None) -> dict[str, Any]:
    """Extract journal info (journal_name, issn, publisher) from primary_location."""
    if not primary_location or not isinstance(primary_location, dict):
        return {"journal_name": None, "issn": None, "publisher": None}

    source = primary_location.get("source", {}) or {}
    if not isinstance(source, dict):
        return {"journal_name": None, "issn": None, "publisher": None}

    return {
        "journal_name": source.get("display_name"),
        "issn": source.get("issn_l"),
        "publisher": source.get("host_organization_name"),
    }


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Reconstruct abstract from OpenAlex inverted index format."""
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


def extract_open_access_info(open_access: dict[str, Any] | None) -> dict[str, Any]:
    """Extract Open Access info (is_oa, oa_status)."""
    if not open_access or not isinstance(open_access, dict):
        return {"is_oa": None, "oa_status": None}

    return {
        "is_oa": open_access.get("is_oa"),
        "oa_status": open_access.get("oa_status"),
    }


def extract_external_ids(ids: dict[str, Any] | None) -> dict[str, Any]:
    """Extract external identifiers (pmid, pmcid, mag_id) from ids object."""
    if not ids or not isinstance(ids, dict):
        return {"pmid": None, "pmcid": None, "mag_id": None}

    # Extract PMID from URL
    # Format: https://pubmed.ncbi.nlm.nih.gov/12345678
    pmid = None
    pmid_url = ids.get("pmid")
    if pmid_url and isinstance(pmid_url, str):
        pmid = pmid_url.rstrip("/").split("/")[-1] if "/" in pmid_url else pmid_url

    # Extract PMCID from URL
    # Format: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123456
    pmcid = None
    pmcid_url = ids.get("pmcid")
    if pmcid_url and isinstance(pmcid_url, str):
        pmcid = pmcid_url.rstrip("/").split("/")[-1] if "/" in pmcid_url else pmcid_url

    # Extract MAG ID (can be int or string)
    mag_id = None
    mag_raw = ids.get("mag")
    if mag_raw is not None:
        mag_id = str(mag_raw)

    return {"pmid": pmid, "pmcid": pmcid, "mag_id": mag_id}


def extract_mesh_terms(mesh: list[dict[str, Any]] | None) -> list[str]:
    """Extract unique MeSH descriptor names from mesh array."""
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


def extract_keywords(keywords: list[dict[str, Any]] | None) -> list[str]:
    """Extract keyword display names from keywords array."""
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


def extract_biblio_info(biblio: dict[str, Any] | None) -> dict[str, Any]:
    """Extract bibliographic info (volume, issue, first_page, last_page)."""
    if not biblio or not isinstance(biblio, dict):
        return {
            "volume": None,
            "issue": None,
            "first_page": None,
            "last_page": None,
        }
    return {
        "volume": biblio.get("volume"),
        "issue": biblio.get("issue"),
        "first_page": biblio.get("first_page"),
        "last_page": biblio.get("last_page"),
    }
