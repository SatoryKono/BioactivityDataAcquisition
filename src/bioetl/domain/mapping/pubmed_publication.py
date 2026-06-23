"""PubMed-specific publication field mapping helpers."""

from __future__ import annotations

PUBMED_SILVER_EXCLUDED_FIELDS: tuple[str, ...] = (
    "vernacular_title",
    "epub_date",
    "received_date",
    "revised_date",
    "accepted_date",
    "citations_received",
)


def build_pubmed_publication_type_fields(
    pub_types: list[str],
    *,
    classification: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    """Build PubMed publication type fields from raw types and classification.

    Args:
        pub_types: List of raw PubMed publication type strings (e.g., ['Journal Article', 'Review']).
        classification: Optional dict of pre-computed unified classification fields to merge in.

    Returns:
        Dictionary with 'publication_type' key set to the raw provider type,
        plus any additional fields from classification if provided.
    """
    raw_type = "|".join(pub_types) if pub_types else None
    result: dict[str, str | None] = {
        "publication_type": raw_type,
    }
    if classification:
        result.update(classification)
    return result


__all__ = [
    "PUBMED_SILVER_EXCLUDED_FIELDS",
    "build_pubmed_publication_type_fields",
]
