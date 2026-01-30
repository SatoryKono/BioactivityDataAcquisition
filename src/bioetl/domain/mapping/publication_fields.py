from typing import Any

from bioetl.domain.value_objects.publication_field_groups import PublicationFieldGroup

PUBLICATION_FIELDS_MAPPING: dict[str, dict[str, Any]] = {
    "pubmed": {
        "title": "article_title",
        "abstract": "abstract_text",
        "doi": "doi",
        "pmid": "pmid",
        "authors": "authors",
        "journal": "journal_title",
        "year": "publication_year",
        "volume": "volume",
        "issue": "issue",
        "pages": "pagination",
        "field_groups": [
            PublicationFieldGroup.BIBLIOGRAPHY,
            PublicationFieldGroup.ID_AND_STATUS,
        ],
    },
    "crossref": {
        "title": "title",
        "abstract": "abstract",
        "doi": "DOI",
        "authors": "author",
        "journal": "container-title",
        "year": "published-print.date-parts.0.0",
        "volume": "volume",
        "issue": "issue",
        "pages": "page",
        "field_groups": [
            PublicationFieldGroup.BIBLIOGRAPHY,
            PublicationFieldGroup.ID_AND_STATUS,
        ],
    },
}
