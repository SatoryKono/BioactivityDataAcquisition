"""Field extraction functions for OpenAlex records.

Contains pure functions for extracting and normalizing fields
from OpenAlex Works API responses.

These functions are:
- Stateless and pure (no side effects)
- Unit testable in isolation
- Reusable across different transformation contexts
"""

from __future__ import annotations

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


def extract_concepts(concepts: list[dict[str, Any]], max_count: int = 10) -> list[str]:
    """Extract top concept names from concepts list.

    OpenAlex provides concepts sorted by relevance score.
    This function extracts the display names of the top concepts.

    Args:
        concepts: List of concept objects (sorted by score).
        max_count: Maximum concepts to extract (default 10).

    Returns:
        List of concept display names.

    Example:
        >>> extract_concepts([
        ...     {"display_name": "Chemistry", "score": 0.9},
        ...     {"display_name": "Biology", "score": 0.7},
        ... ])
        ['Chemistry', 'Biology']
    """
    result = []
    for concept in concepts[:max_count]:
        if not isinstance(concept, dict):
            continue
        name = concept.get("display_name")
        if name and isinstance(name, str):
            result.append(name.strip())
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

    Args:
        ids: IDs object from OpenAlex work.

    Returns:
        Dictionary with pmid, pmcid, mag_id fields.

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
