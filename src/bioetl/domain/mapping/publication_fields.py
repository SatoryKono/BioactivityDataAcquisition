from typing import Any

from bioetl.domain.value_objects.publication_field_groups import PublicationFieldGroup


PUBLICATION_FIELDS_MAPPING: dict[str, Any] = {
    # Common fields
    "pmid": PublicationFieldGroup.ID_AND_STATUS,
    "doi": PublicationFieldGroup.ID_AND_STATUS,
    "pmc_id": PublicationFieldGroup.ID_AND_STATUS,
    "title": PublicationFieldGroup.BIBLIOGRAPHY,
    "abstract": PublicationFieldGroup.BIBLIOGRAPHY,
    "journal": PublicationFieldGroup.BIBLIOGRAPHY,
    "journal_name_short": PublicationFieldGroup.BIBLIOGRAPHY,
    "publication_year": PublicationFieldGroup.DATE_AND_PLACES,
    "publication_date": PublicationFieldGroup.DATE_AND_PLACES,
    "volume": PublicationFieldGroup.BIBLIOGRAPHY,
    "issue": PublicationFieldGroup.BIBLIOGRAPHY,
    "page_first": PublicationFieldGroup.BIBLIOGRAPHY,
    "page_last": PublicationFieldGroup.BIBLIOGRAPHY,
    "issn": PublicationFieldGroup.BIBLIOGRAPHY,
    "issn_print": PublicationFieldGroup.BIBLIOGRAPHY,
    "issn_electronic": PublicationFieldGroup.BIBLIOGRAPHY,
    "language": PublicationFieldGroup.TRASH,
    "publication_type": PublicationFieldGroup.ID_AND_STATUS,
    "publisher": PublicationFieldGroup.BIBLIOGRAPHY,
    "license_url": PublicationFieldGroup.TRASH,
    "is_oa": PublicationFieldGroup.ID_AND_STATUS,
    "citations_received": PublicationFieldGroup.CITATIONS_AND_REFERENCE,
    "citations_made": PublicationFieldGroup.CITATIONS_AND_REFERENCE,
    "content_domain_domains": PublicationFieldGroup.TRASH,
    "content_domain_crossmark_restriction": PublicationFieldGroup.TRASH,

    # Author and affiliation fields
    "authors": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "affiliation_list": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "author_details": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "author_orcid_list": PublicationFieldGroup.TRASH,  # Deprecated
    "author_orcids": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,  # Legacy

    # List fields
    "issn_list": PublicationFieldGroup.BIBLIOGRAPHY,
    "subject_keywords": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
    "references": PublicationFieldGroup.CITATIONS_AND_REFERENCE,

    # Internal fields
    "entity_id": PublicationFieldGroup.ID_AND_STATUS,
    "content_hash": PublicationFieldGroup.TRASH,
    "_run_id": PublicationFieldGroup.ID_AND_STATUS,
    "_run_type": PublicationFieldGroup.ID_AND_STATUS,
    "_source_batch_id": PublicationFieldGroup.ID_AND_STATUS,
    "_ingestion_ts": PublicationFieldGroup.ID_AND_STATUS,
    "_dq_warn": PublicationFieldGroup.ID_AND_STATUS,
    "_dq_error": PublicationFieldGroup.ID_AND_STATUS,
    "_index": PublicationFieldGroup.ID_AND_STATUS,
    "_lookup_method": PublicationFieldGroup.ID_AND_STATUS,
    "_original_id": PublicationFieldGroup.ID_AND_STATUS,
    "_source": PublicationFieldGroup.ID_AND_STATUS,

    # Deprecated / Trash fields
    "published_print": PublicationFieldGroup.TRASH,
    "published_online": PublicationFieldGroup.TRASH,
    "alternative_id": PublicationFieldGroup.ID_AND_STATUS,
    "published": PublicationFieldGroup.TRASH,
}


def get_field_group(field_name: str) -> Any:
    """Get the group for a given field name."""
    return PUBLICATION_FIELDS_MAPPING.get(field_name, PublicationFieldGroup.TRASH)
