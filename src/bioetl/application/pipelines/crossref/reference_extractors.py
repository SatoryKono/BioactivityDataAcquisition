"""Reference extraction functions for CrossRef records.

Provides pure functions for extracting bibliographic references from
CrossRef Works API responses for citation network analysis.

These functions are:
- Stateless and pure (no side effects)
- Unit testable in isolation
- Reusable across different transformation contexts
"""

from __future__ import annotations

__all__ = ["extract_references"]


from bioetl.domain.types import JsonDict


def _clean_string(
    value: object,
    lowercase: bool = False,
) -> str | None:
    """Clean and optionally lowercase a string value."""
    if not value or not isinstance(value, str):
        return None
    cleaned: str = value.strip()
    if not cleaned:
        return None
    return cleaned.lower() if lowercase else cleaned


def _parse_year(year_raw: object) -> int | None:
    """Parse year from string or int value."""
    if not year_raw:
        return None
    if isinstance(year_raw, int):
        return year_raw
    if isinstance(year_raw, str):
        year_str = year_raw.strip()
        if year_str.isdigit():
            return int(year_str)
    return None


# Any: raw API JSON
def extract_references(
    publication: JsonDict,  # Any: untyped API JSON record
) -> list[JsonDict]:  # Any: untyped API JSON record
    """Extract bibliographic references from CrossRef publication.

    Parses the 'reference' array containing citations to other works.
    This data is essential for citation network analysis and bibliometric studies.

    Args:
        publication: CrossRef publication record.

    Returns:
        List of reference dictionaries with normalized keys.
        Each reference contains available bibliographic metadata.

    """
    references: list[JsonDict] = []  # Any: heterogeneous reference field values
    raw_references = publication.get("reference", [])
    # Crossref ``reference`` is list-only; treat missing/None/non-list as empty.
    if not isinstance(raw_references, list):
        return references
    for ref in raw_references:
        if not isinstance(ref, dict):
            continue
        references.append(
            {
                "key": _clean_string(ref.get("key")),
                "doi": _clean_string(ref.get("DOI"), lowercase=True),
                "doi_asserted_by": _clean_string(
                    ref.get("doi-asserted-by"), lowercase=True
                ),
                "article_title": _clean_string(ref.get("article-title")),
                "volume_title": _clean_string(ref.get("volume-title")),
                "journal_title": _clean_string(ref.get("journal-title")),
                "series_title": _clean_string(ref.get("series-title")),
                "author": _clean_string(ref.get("author")),
                "year": _parse_year(ref.get("year")),
                "volume": _clean_string(ref.get("volume")),
                "issue": _clean_string(ref.get("issue")),
                "first_page": _clean_string(ref.get("first-page")),
                "unstructured": _clean_string(ref.get("unstructured")),
                "issn": _clean_string(ref.get("ISSN")),
                "isbn": _clean_string(ref.get("ISBN")),
            }
        )
    return references
