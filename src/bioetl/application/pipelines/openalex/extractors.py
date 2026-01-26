"""Field extraction functions for OpenAlex records.

Contains pure functions for extracting and normalizing fields
from OpenAlex Works API responses.

These functions are:
- Stateless and pure (no side effects)
- Unit testable in isolation
- Reusable across different transformation contexts

Note on Topics vs Concepts:
- OpenAlex deprecated the `concepts` field in 2024 in favor of `topics`
- Topics provide a 4-level hierarchy: domain -> field -> subfield -> topic
- The `extract_concepts()` function is kept for backward compatibility
- New code should use `extract_topics()` and `extract_primary_topic()`
"""

from __future__ import annotations

import warnings
from typing import Any


def extract_doi(doi_url: str | None) -> str | None:
    """Extract bare DOI from OpenAlex DOI URL.

    OpenAlex stores DOIs as full URLs (e.g., "https://doi.org/10.1038/s41586-024-07487-w").
    This function extracts just the DOI identifier.

    Args:
        doi_url: DOI URL from OpenAlex (e.g., "https://doi.org/10.1038/...").

    Returns:
        Bare DOI (e.g., "10.1038/s41586-024-07487-w") or None if not available.

    Example:
        >>> extract_doi("https://doi.org/10.1038/s41586-024-07487-w")
        '10.1038/s41586-024-07487-w'
        >>> extract_doi(None)
        None
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

    OpenAlex stores IDs as full URLs (e.g., "https://openalex.org/W2148763428").
    This function extracts just the Work ID.

    Args:
        openalex_url: OpenAlex URL (e.g., "https://openalex.org/W2148763428").

    Returns:
        OpenAlex Work ID (e.g., "W2148763428") or None if not available.

    Example:
        >>> extract_openalex_id("https://openalex.org/W2148763428")
        'W2148763428'
        >>> extract_openalex_id(None)
        None
    """
    if not openalex_url:
        return None
    if "/" in openalex_url:
        return openalex_url.split("/")[-1]
    return openalex_url


def extract_authors(authorships: list[dict[str, Any]]) -> list[str]:
    """Extract author display names from authorships.

    OpenAlex stores author information in an "authorships" array with
    nested "author" objects containing display names.

    Args:
        authorships: List of authorship objects from OpenAlex.

    Returns:
        List of author display names.

    Example:
        >>> extract_authors([
        ...     {"author": {"display_name": "John Doe"}},
        ...     {"author": {"display_name": "Jane Smith"}},
        ... ])
        ['John Doe', 'Jane Smith']
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


def extract_affiliations(authorships: list[dict[str, Any]]) -> list[str]:
    """Extract unique affiliations from authorships.

    OpenAlex stores affiliations inside authorships -> institutions.

    Args:
        authorships: List of authorship objects from OpenAlex.

    Returns:
        List of unique affiliation display names (sorted).

    Example:
        >>> extract_affiliations([
        ...     {"institutions": [{"display_name": "Harvard University"}]},
        ...     {"institutions": [{"display_name": "MIT"}, {"display_name": "Harvard University"}]}
        ... ])
        ['Harvard University', 'MIT']
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


def extract_concepts(
    concepts: list[dict[str, Any]],
    max_count: int = 10,
    *,
    warn_deprecated: bool = False,
) -> list[str]:
    """Extract top concept names from concepts list.

    .. deprecated::
        OpenAlex deprecated the `concepts` field in 2024 in favor of `topics`.
        Use :func:`extract_topics` and :func:`extract_primary_topic` instead.
        This function is kept for backward compatibility during the transition.

    OpenAlex provides concepts sorted by relevance score.
    This function extracts the display names of the top concepts.

    Args:
        concepts: List of concept objects (sorted by score).
        max_count: Maximum concepts to extract (default 10).
        warn_deprecated: If True, emit a deprecation warning. Default False
            to avoid noise during transition period.

    Returns:
        List of concept display names.

    Example:
        >>> extract_concepts([
        ...     {"display_name": "Chemistry", "score": 0.9},
        ...     {"display_name": "Biology", "score": 0.7},
        ... ])
        ['Chemistry', 'Biology']
    """
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
    """Extract topics with hierarchical classification from topics list.

    OpenAlex topics provide a 4-level hierarchy:
    - domain: Broadest level (e.g., "Physical Sciences")
    - field: Second level (e.g., "Chemistry")
    - subfield: Third level (e.g., "Organic Chemistry")
    - topic: Most specific (e.g., "Synthesis of Organic Compounds")

    Each topic includes a relevance score (0-1) indicating confidence.

    Args:
        topics: List of topic objects from OpenAlex API.
        max_count: Maximum topics to extract (default 10).

    Returns:
        List of topic dictionaries with keys:
        - id: OpenAlex topic ID (e.g., "T12345")
        - display_name: Topic name
        - score: Relevance score (0-1)
        - subfield: Subfield name
        - field: Field name
        - domain: Domain name

    Example:
        >>> extract_topics([
        ...     {
        ...         "id": "https://openalex.org/T12345",
        ...         "display_name": "Organic Synthesis",
        ...         "score": 0.95,
        ...         "subfield": {"display_name": "Organic Chemistry"},
        ...         "field": {"display_name": "Chemistry"},
        ...         "domain": {"display_name": "Physical Sciences"}
        ...     }
        ... ])
        [{'id': 'T12345', 'display_name': 'Organic Synthesis', 'score': 0.95,
          'subfield': 'Organic Chemistry', 'field': 'Chemistry',
          'domain': 'Physical Sciences'}]
    """
    if not topics or not isinstance(topics, list):
        return []

    result: list[dict[str, Any]] = []
    for topic in topics[:max_count]:
        if not isinstance(topic, dict):
            continue

        # Extract topic ID from URL
        topic_id = topic.get("id")
        if topic_id and isinstance(topic_id, str) and "/" in topic_id:
            topic_id = topic_id.split("/")[-1]

        display_name = topic.get("display_name")
        if not display_name or not isinstance(display_name, str):
            continue

        # Extract score (default to 0 if missing)
        score = topic.get("score")
        if not isinstance(score, (int, float)):
            score = 0.0

        # Extract hierarchical classification
        subfield = topic.get("subfield", {}) or {}
        field = topic.get("field", {}) or {}
        domain = topic.get("domain", {}) or {}

        result.append({
            "id": topic_id,
            "display_name": display_name.strip(),
            "score": float(score),
            "subfield": subfield.get("display_name") if isinstance(subfield, dict) else None,
            "field": field.get("display_name") if isinstance(field, dict) else None,
            "domain": domain.get("display_name") if isinstance(domain, dict) else None,
        })

    return result


def extract_primary_topic(primary_topic: dict[str, Any] | None) -> dict[str, Any] | None:
    """Extract primary topic classification from primary_topic field.

    The primary_topic is the single most relevant topic for a work,
    useful for quick categorization without examining all topics.

    Args:
        primary_topic: Primary topic object from OpenAlex API.

    Returns:
        Dictionary with topic info or None if not available.
        Keys: id, display_name, score, subfield, field, domain

    Example:
        >>> extract_primary_topic({
        ...     "id": "https://openalex.org/T12345",
        ...     "display_name": "Organic Synthesis",
        ...     "score": 0.95,
        ...     "subfield": {"display_name": "Organic Chemistry"},
        ...     "field": {"display_name": "Chemistry"},
        ...     "domain": {"display_name": "Physical Sciences"}
        ... })
        {'id': 'T12345', 'display_name': 'Organic Synthesis', 'score': 0.95,
         'subfield': 'Organic Chemistry', 'field': 'Chemistry',
         'domain': 'Physical Sciences'}
    """
    if not primary_topic or not isinstance(primary_topic, dict):
        return None

    # Extract topic ID from URL
    topic_id = primary_topic.get("id")
    if topic_id and isinstance(topic_id, str) and "/" in topic_id:
        topic_id = topic_id.split("/")[-1]

    display_name = primary_topic.get("display_name")
    if not display_name or not isinstance(display_name, str):
        return None

    # Extract score (default to 0 if missing)
    score = primary_topic.get("score")
    if not isinstance(score, (int, float)):
        score = 0.0

    # Extract hierarchical classification
    subfield = primary_topic.get("subfield", {}) or {}
    field = primary_topic.get("field", {}) or {}
    domain = primary_topic.get("domain", {}) or {}

    return {
        "id": topic_id,
        "display_name": display_name.strip(),
        "score": float(score),
        "subfield": subfield.get("display_name") if isinstance(subfield, dict) else None,
        "field": field.get("display_name") if isinstance(field, dict) else None,
        "domain": domain.get("display_name") if isinstance(domain, dict) else None,
    }


def extract_grants(grants: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Extract grant/funding information from grants array.

    OpenAlex provides funding information including funder name and award ID,
    useful for research funding analysis and compliance reporting.

    Args:
        grants: List of grant objects from OpenAlex API.

    Returns:
        List of grant dictionaries with keys:
        - funder: Funder OpenAlex ID (e.g., "F1234567")
        - funder_display_name: Funder name (e.g., "National Institutes of Health")
        - award_id: Grant/award identifier (may be None)

    Example:
        >>> extract_grants([
        ...     {
        ...         "funder": "https://openalex.org/F1234567",
        ...         "funder_display_name": "National Institutes of Health",
        ...         "award_id": "R01-GM123456"
        ...     }
        ... ])
        [{'funder': 'F1234567', 'funder_display_name': 'National Institutes of Health',
          'award_id': 'R01-GM123456'}]
    """
    if not grants or not isinstance(grants, list):
        return []

    result: list[dict[str, Any]] = []
    for grant in grants:
        if not isinstance(grant, dict):
            continue

        # Extract funder ID from URL
        funder_id = grant.get("funder")
        if funder_id and isinstance(funder_id, str) and "/" in funder_id:
            funder_id = funder_id.split("/")[-1]

        funder_name = grant.get("funder_display_name")
        if not funder_name or not isinstance(funder_name, str):
            # Skip grants without funder name
            continue

        award_id = grant.get("award_id")
        if award_id and not isinstance(award_id, str):
            award_id = str(award_id)

        result.append({
            "funder": funder_id,
            "funder_display_name": funder_name.strip(),
            "award_id": award_id.strip() if award_id else None,
        })

    return result


def extract_journal_info(primary_location: dict[str, Any] | None) -> dict[str, Any]:
    """Extract journal information from primary_location.

    OpenAlex stores source information in "primary_location.source".
    This function extracts journal name, ISSN, and publisher.

    Args:
        primary_location: Primary location object from OpenAlex.

    Returns:
        Dictionary with journal_name, issn, publisher.

    Example:
        >>> extract_journal_info({
        ...     "source": {
        ...         "display_name": "Nature",
        ...         "issn_l": "0028-0836",
        ...         "host_organization_name": "Springer Nature"
        ...     }
        ... })
        {'journal_name': 'Nature', 'issn': '0028-0836', 'publisher': 'Springer Nature'}
    """
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
    """Reconstruct abstract from OpenAlex inverted index.

    OpenAlex stores abstracts as inverted index format for storage efficiency:
    {"word": [positions]}.
    This function reconstructs the original text.

    Args:
        inverted_index: Dict mapping words to position lists.

    Returns:
        Reconstructed abstract text or None if not available.

    Example:
        >>> reconstruct_abstract({
        ...     "This": [0],
        ...     "is": [1, 4],
        ...     "an": [2],
        ...     "example": [3],
        ...     "abstract": [5]
        ... })
        'This is an example is abstract'
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


def extract_open_access_info(open_access: dict[str, Any] | None) -> dict[str, Any]:
    """Extract Open Access information from open_access object.

    Args:
        open_access: Open access object from OpenAlex.

    Returns:
        Dictionary with is_oa and oa_status.

    Example:
        >>> extract_open_access_info({"is_oa": True, "oa_status": "gold"})
        {'is_oa': True, 'oa_status': 'gold'}
    """
    if not open_access or not isinstance(open_access, dict):
        return {"is_oa": None, "oa_status": None}

    return {
        "is_oa": open_access.get("is_oa"),
        "oa_status": open_access.get("oa_status"),
    }


def extract_external_ids(ids: dict[str, Any] | None) -> dict[str, Any]:
    """Extract external identifiers from ids object.

    OpenAlex stores external IDs as URLs or raw values:
    - pmid: "https://pubmed.ncbi.nlm.nih.gov/12345678" -> "12345678"
    - pmcid: "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123456" -> "PMC123456"
    - mag: Microsoft Academic Graph ID (integer or string)

    Note: Returns intermediate keys matching API names. Transformer maps
    pmcid -> pmc_id for schema consistency.

    Args:
        ids: IDs object from OpenAlex work.

    Returns:
        Dictionary with pmid, pmcid (maps to pmc_id in transformer), mag_id fields.

    Example:
        >>> extract_external_ids({
        ...     "pmid": "https://pubmed.ncbi.nlm.nih.gov/32015508",
        ...     "pmcid": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7095418",
        ...     "mag": "3006090887"
        ... })
        {'pmid': '32015508', 'pmcid': 'PMC7095418', 'mag_id': '3006090887'}
        >>> extract_external_ids(None)
        {'pmid': None, 'pmcid': None, 'mag_id': None}
    """
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
    """Extract MeSH descriptor names from mesh array.

    OpenAlex provides MeSH terms with descriptor and qualifier info.
    This function extracts unique descriptor names.

    Args:
        mesh: List of MeSH term objects from OpenAlex.

    Returns:
        List of unique MeSH descriptor names.

    Example:
        >>> extract_mesh_terms([
        ...     {"descriptor_ui": "D000818", "descriptor_name": "Animals"},
        ...     {"descriptor_ui": "D006801", "descriptor_name": "Humans"},
        ...     {"descriptor_ui": "D000818", "descriptor_name": "Animals"}
        ... ])
        ['Animals', 'Humans']
        >>> extract_mesh_terms(None)
        []
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


def extract_keywords(keywords: list[dict[str, Any]] | None) -> list[str]:
    """Extract keyword display names from keywords array.

    OpenAlex provides keywords with display_name field.

    Args:
        keywords: List of keyword objects from OpenAlex.

    Returns:
        List of keyword display names.

    Example:
        >>> extract_keywords([
        ...     {"id": "https://openalex.org/keywords/coronavirus", "display_name": "Coronavirus"},
        ...     {"id": "https://openalex.org/keywords/pandemic", "display_name": "Pandemic"}
        ... ])
        ['Coronavirus', 'Pandemic']
        >>> extract_keywords(None)
        []
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


def extract_biblio_info(biblio: dict[str, Any] | None) -> dict[str, Any]:
    """Extract bibliographic info (volume, issue, pages) from biblio object.

    OpenAlex provides bibliographic information in a "biblio" object
    containing volume, issue, first_page, and last_page fields.

    Args:
        biblio: Biblio object from OpenAlex work.

    Returns:
        Dictionary with volume, issue, first_page, last_page.

    Example:
        >>> extract_biblio_info({
        ...     "volume": "42",
        ...     "issue": "3",
        ...     "first_page": "123",
        ...     "last_page": "145"
        ... })
        {'volume': '42', 'issue': '3', 'first_page': '123', 'last_page': '145'}
        >>> extract_biblio_info(None)
        {'volume': None, 'issue': None, 'first_page': None, 'last_page': None}
    """
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
