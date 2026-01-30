from typing import Any

from bioetl.domain.value_objects.publication_field_groups import PublicationFieldGroup

PUBLICATION_FIELDS_MAPPING: dict[str, dict[str, Any]] = {
    "pubmed": {
        "pmid": "pmid",
        "doi": "doi",
        "title": "title",
        "abstract": "abstract",
        "journal": "journal",
        "journal_title": "journal",  # Legacy alias
        "journal_iso": "journal_iso",
        "journal_issn": "journal_issn",
        "publication_date": "publication_date",
        "year": "year",
        "authors": "authors",
        "affiliations": "affiliations",
        "language": "language",
        "publication_type": "publication_type",
        "keywords": "keywords",
        "mesh_terms": "mesh_terms",
        "chemicals": "chemicals",
        "citations": "citations",
        "references": "references",
        "pmc_id": "pmc_id",
        "license": "license",
        "copyright": "copyright",
        "publisher": "publisher",
    },
    "crossref": {
        "DOI": "doi",
        "title": "title",
        "abstract": "abstract",
        "container-title": "journal",
        "short-container-title": "journal_iso",
        "ISSN": "journal_issn",
        "published": "publication_date",
        "issued": "publication_date",  # Fallback
        "created": "created_date",
        "author": "authors",
        "publisher": "publisher",
        "type": "publication_type",
        "language": "language",
        "reference": "references",
        "is-referenced-by-count": "citation_count",
        "URL": "url",
        "link": "links",
        "license": "license",
        "subject": "keywords",
    },
}

# Invert the mapping for internal use (Unified -> Provider)
UNIFIED_TO_PROVIDER: dict[str, dict[str, str]] = {
    provider: {v: k for k, v in mapping.items() if isinstance(v, str)}
    for provider, mapping in PUBLICATION_FIELDS_MAPPING.items()
}


def apply_field_mapping(
    data: dict[str, Any], provider: str, strict: bool = False
) -> dict[str, Any]:
    """
    Map provider-specific fields to unified schema fields.

    Args:
        data: Dictionary of data from provider
        provider: Provider name (pubmed, crossref, etc)
        strict: If True, only include mapped fields

    Returns:
        Dictionary with unified field names
    """
    if provider not in PUBLICATION_FIELDS_MAPPING:
        return data

    mapping = PUBLICATION_FIELDS_MAPPING[provider]
    result = {}

    for key, value in data.items():
        if key in mapping:
            unified_key = mapping[key]
            result[unified_key] = value
        elif not strict:
            result[key] = value

    return result


def get_provider_name(unified_name: str, provider: str) -> str | None:
    """Get the provider-specific name for a unified field."""
    return UNIFIED_TO_PROVIDER.get(provider, {}).get(unified_name)


def get_unified_name(provider_name: str, provider: str) -> str | None:
    """Get the unified name for a provider-specific field."""
    return PUBLICATION_FIELDS_MAPPING.get(provider, {}).get(provider_name)
