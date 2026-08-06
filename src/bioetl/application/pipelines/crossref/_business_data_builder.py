"""Internal helpers for CrossRef business-data assembly."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from bioetl.application.core.base_transformer_helpers_mixin import ScalarValue
from bioetl.application.pipelines.crossref.extractors import (
    extract_author_details,
    extract_author_orcids,
    extract_authors,
    extract_content_domain,
    extract_dates,
    extract_issn_by_type,
    extract_journal_info,
    extract_license_url,
    extract_page_info,
    extract_published_date,
    extract_references,
)
from bioetl.domain.normalization import extract_first_string
from bioetl.domain.types import GoldRecord, JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import DataNormalizationPort


def compute_publication_date(
    published_print: str | None,
    published_online: str | None,
) -> str | None:
    """Select unified publication date, preferring print.

    Args:
        published_print: Print publication date string, or None.
        published_online: Online publication date string, or None.

    Returns:
        Print date if available, otherwise online date, or None if both are absent.
    """
    return published_print or published_online


def hash_author_details(
    author_details: list[JsonDict],  # Any: raw CrossRef API JSON fragments
    *,
    hash_pii_value: Callable[[str | None], str | None],
) -> list[JsonDict]:
    """Hash PII fields in author details while preserving non-PII fields.

    Args:
        author_details: Raw CrossRef author detail dicts from the API response.
        hash_pii_value: Callable that hashes a string PII value to its digest.

    Returns:
        List of author dicts with given, family, and name fields hashed.
    """
    hashed_details: list[JsonDict] = []  # Any: raw CrossRef API JSON fragments

    for author in author_details:
        hashed_author: JsonDict = {}  # Any: heterogeneous JSON values
        for pii_field in ("given", "family", "name"):
            value = author.get(pii_field)
            hashed_author[pii_field] = (
                hash_pii_value(value) if isinstance(value, str) and value else None
            )

        # ORCID and affiliation data are not PII; preserve original values.
        hashed_author["orcid"] = author.get("orcid")
        hashed_author["authenticated_orcid"] = author.get("authenticated_orcid")
        hashed_author["sequence"] = author.get("sequence")
        hashed_author["affiliations"] = author.get("affiliations", [])
        hashed_details.append(hashed_author)

    return hashed_details


def extract_publication_year_candidate(
    record: JsonDict,  # Any: raw CrossRef API record
) -> int | None:
    """Extract first available publication year from CrossRef date-parts.

    Args:
        record: Raw CrossRef API record dict containing date fields.

    Returns:
        Integer year from the first available date field, or None if not found.
    """
    for date_field in ("published-print", "published-online", "issued"):
        date_info = record.get(date_field)
        if not isinstance(date_info, dict):
            continue

        date_parts = date_info.get("date-parts")
        if not isinstance(date_parts, list) or not date_parts:
            continue

        first_part = date_parts[0]
        if not isinstance(first_part, list) or not first_part:
            continue

        year_raw = first_part[0]
        if isinstance(year_raw, int):
            return year_raw
        if isinstance(year_raw, str) and year_raw.isdigit():
            return int(year_raw)
    return None


def _extract_author_bundle(
    record: JsonDict,  # Any: raw CrossRef API record
    *,
    data_normalizer: DataNormalizationPort,
    hash_pii_value: Callable[[str | None], str | None],
    serialize_json: Callable[[object], ScalarValue],
    serialize_json_list: Callable[[Sequence[object] | None], str | None],
) -> dict[str, str | None]:
    """Extract and normalize all author-related fields in one orchestration block."""
    raw_authors = extract_authors(record)
    authors_json = data_normalizer.normalize_author_list(raw_authors)
    author_keys = data_normalizer.normalize_author_keys(raw_authors)

    raw_author_details = extract_author_details(record)
    hashed_author_details = hash_author_details(
        raw_author_details,
        hash_pii_value=hash_pii_value,
    )
    author_details_raw_json = serialize_json(raw_author_details)
    author_details_canonical_json = serialize_json(hashed_author_details)

    author_orcids = extract_author_orcids(record)
    serialized_orcids = serialize_json_list(author_orcids)

    affiliations_input = _extract_affiliations_input(raw_author_details)
    affiliations_json = data_normalizer.normalize_affiliations(affiliations_input)

    return {
        "authors": authors_json,
        "author_keys": author_keys,
        "author_orcids": serialized_orcids,
        "author_details": (
            author_details_canonical_json
            if isinstance(author_details_canonical_json, str)
            else None
        ),
        "author_details_raw_json": (
            author_details_raw_json
            if isinstance(author_details_raw_json, str)
            else None
        ),
        "author_details_canonical_json": (
            author_details_canonical_json
            if isinstance(author_details_canonical_json, str)
            else None
        ),
        "affiliation_list": affiliations_json,
    }


def _extract_affiliations_input(
    raw_author_details: list[JsonDict],
) -> list[str] | list[JsonDict] | None:
    """Extract affiliations from author details, preferring dicts over strings."""
    affiliation_strings: list[str] = []
    affiliation_dicts: list[JsonDict] = []
    for author in raw_author_details:
        raw_affiliations = author.get("affiliations", [])
        if not isinstance(raw_affiliations, list):
            continue
        for affiliation in raw_affiliations:
            if isinstance(affiliation, str):
                affiliation_strings.append(affiliation)
            elif isinstance(affiliation, dict):
                affiliation_dicts.append(affiliation)

    if affiliation_dicts:
        return affiliation_dicts
    if affiliation_strings:
        return affiliation_strings
    return None


def _build_crossref_identity_fields(
    *,
    record: JsonDict,
    doi: str,
    author_bundle: dict[str, str | None],
) -> GoldRecord:
    """Build identity and publication-core fields for CrossRef payloads."""
    return {
        "doi": doi,
        # Required PublicationBaseSchema fields unavailable in CrossRef payload.
        "pmid": None,
        "pmc_id": None,
        "abstract": None,
        "title": extract_first_string(record.get("title", [])),
        **author_bundle,
        "_source": "crossref",
        "_lookup_method": record.get("_lookup_method", "doi"),
        "_original_id": record.get("_original_id"),
    }


def build_crossref_core_block_fields(
    *,
    record: JsonDict,
    doi: str,
    classify_publication_type: Callable[[str | None], dict[str, str | None]],
    serialize_json_list: Callable[[Sequence[object] | None], str | None],
) -> GoldRecord:
    """Build the declarative core-block field set from shared business helpers."""
    return {
        **_build_crossref_identity_fields(
            record=record,
            doi=doi,
            author_bundle={},
        ),
        **classify_publication_type(record.get("type")),
        "language": record.get("language"),
        "is_oa": None,
        "alternative_id": serialize_json_list(record.get("alternative-id", []) or []),
        "subject_keywords": serialize_json_list(record.get("subject", []) or []),
        "_dq_warn": False,
        "_dq_error": False,
    }


def build_crossref_author_block_fields(
    record: JsonDict,
    *,
    data_normalizer: DataNormalizationPort,
    hash_pii_value: Callable[[str | None], str | None],
    serialize_json: Callable[[object], ScalarValue],
    serialize_json_list: Callable[[Sequence[object] | None], str | None],
) -> dict[str, str | None]:
    """Build the declarative author-block field set from shared business helpers."""
    return _extract_author_bundle(
        record,
        data_normalizer=data_normalizer,
        hash_pii_value=hash_pii_value,
        serialize_json=serialize_json,
        serialize_json_list=serialize_json_list,
    )


def _build_crossref_metadata_fields(
    *,
    record: JsonDict,
    journal_info: JsonDict,
    page_info: JsonDict,
    dates: JsonDict,
    content_domain: JsonDict,
    issn_by_type: JsonDict,
    published_date: str | None,
    publication_date: str | None,
    publication_year: int | None,
    classify_publication_type: Callable[[str | None], dict[str, str | None]],
    serialize_json_list: Callable[[Sequence[object] | None], str | None],
) -> GoldRecord:
    """Build publication metadata fields for CrossRef payloads."""
    return {
        **journal_info,
        **page_info,
        **dates,
        "publication_year": publication_year,
        "publication_date": publication_date,
        **classify_publication_type(record.get("type")),
        "citations_received": record.get("is-referenced-by-count"),
        "citations_made": record.get("references-count"),
        "language": record.get("language"),
        "license_url": extract_license_url(record),
        "subject_keywords": serialize_json_list(record.get("subject", []) or []),
        "is_oa": None,
        "alternative_id": serialize_json_list(record.get("alternative-id", []) or []),
        "journal_name_short": extract_first_string(record.get("short-container-title")),
        "published": published_date,
        "content_domain_domains": serialize_json_list(
            content_domain.get("content_domain_domains", [])
        ),
        "content_domain_crossmark_restriction": content_domain.get(
            "content_domain_crossmark_restriction"
        ),
        **issn_by_type,
    }


def _build_crossref_reference_fields(
    *,
    record: JsonDict,
    references: str | None,
    references_raw_json: str | None,
    references_canonical_json: str | None,
) -> GoldRecord:
    """Build reference and DQ fields for CrossRef payloads."""
    del record
    return {
        "references": references,
        "references_raw_json": references_raw_json,
        "references_canonical_json": references_canonical_json,
        # DQ flags (MUST be last, per RULES.md §2.4)
        "_dq_warn": False,
        "_dq_error": False,
    }


def build_crossref_business_data(
    record: JsonDict,  # Any: raw CrossRef API record
    *,
    data_normalizer: DataNormalizationPort,
    validate_doi: Callable[[object], str | None],
    validate_publication_year: Callable[[object], int | None],
    classify_publication_type: Callable[[str | None], dict[str, str | None]],
    serialize_json: Callable[[object], ScalarValue],
    serialize_json_list: Callable[[Sequence[object] | None], str | None],
    hash_pii_value: Callable[[str | None], str | None],
) -> GoldRecord:
    """Build CrossRef publication business-data payload.

    Args:
        record: Raw CrossRef API record dict.
        data_normalizer: Port for author list and affiliation normalization.
        validate_doi: Callable that validates and normalizes a DOI string.
        validate_publication_year: Callable that validates a raw year value.
        classify_publication_type: Callable returning publication type classification dict.
        serialize_json: Callable that serializes a value to a JSON scalar string.
        serialize_json_list: Callable that serializes a sequence to a JSON array string.
        hash_pii_value: Callable that hashes a string PII value to its digest.

    Returns:
        GoldRecord dict with all CrossRef publication fields populated.
    """
    doi = validate_doi(record.get("DOI"))
    assert doi is not None, "DOI should be validated in _pre_extract_validation"

    journal_info = extract_journal_info(record)
    page_info = extract_page_info(record)
    dates = extract_dates(record)
    content_domain = extract_content_domain(record)
    issn_by_type = extract_issn_by_type(record)
    published_date = extract_published_date(record)
    author_bundle = _extract_author_bundle(
        record,
        data_normalizer=data_normalizer,
        hash_pii_value=hash_pii_value,
        serialize_json=serialize_json,
        serialize_json_list=serialize_json_list,
    )

    publication_date = compute_publication_date(
        dates.get("published_print"),
        dates.get("published_online"),
    )
    raw_year = extract_publication_year_candidate(record)
    # Preserve original CrossRef ``reference`` payload before normalization.
    references_raw_json = serialize_json(record.get("reference"))
    normalized_references = extract_references(record)
    references_canonical_json = serialize_json(normalized_references)

    return {
        **_build_crossref_identity_fields(
            record=record,
            doi=doi,
            author_bundle=author_bundle,
        ),
        **_build_crossref_metadata_fields(
            record=record,
            journal_info=journal_info,
            page_info=page_info,
            dates=dates,
            content_domain=content_domain,
            issn_by_type=issn_by_type,
            published_date=published_date,
            publication_date=publication_date,
            publication_year=validate_publication_year(raw_year),
            classify_publication_type=classify_publication_type,
            serialize_json_list=serialize_json_list,
        ),
        **_build_crossref_reference_fields(
            record=record,
            references=(
                references_canonical_json
                if isinstance(references_canonical_json, str)
                else None
            ),
            references_raw_json=(
                references_raw_json if isinstance(references_raw_json, str) else None
            ),
            references_canonical_json=(
                references_canonical_json
                if isinstance(references_canonical_json, str)
                else None
            ),
        ),
    }
