"""Private declarative extraction helpers for the CrossRef pipeline."""

from __future__ import annotations

from collections.abc import Callable, Sequence

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
from bioetl.domain.ports import DataNormalizationPort
from bioetl.domain.types import BronzeRecord, JsonDict


def _extract_crossref_publication_year_candidate(
    record: BronzeRecord,
) -> int | None:
    """Extract the first available CrossRef year from date-parts payloads."""
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


class _CrossRefCoreBlock:
    """Extracts core CrossRef identifiers, titles, and publication types."""

    def __init__(
        self,
        validate_doi: Callable[[object], str | None],
        classify_pub_type: Callable[[str | None], dict[str, str | None]],
        serialize_json_list: Callable[[Sequence[object] | None], str | None],
    ) -> None:
        self.validate_doi = validate_doi
        self.classify_pub_type = classify_pub_type
        self.serialize_json_list = serialize_json_list

    def extract(self, record: BronzeRecord) -> JsonDict:
        doi = self.validate_doi(record.get("DOI"))
        assert doi is not None, "DOI should be validated in _pre_extract_validation"
        raw_type = record.get("type")

        return {
            "doi": doi,
            "pmid": None,
            "pmc_id": None,
            "abstract": None,
            "title": extract_first_string(record.get("title", [])),
            **self.classify_pub_type(raw_type),
            "language": record.get("language"),
            "_source": "crossref",
            "is_oa": None,
            "_lookup_method": record.get("_lookup_method", "doi"),
            "_original_id": record.get("_original_id"),
            "alternative_id": self.serialize_json_list(
                record.get("alternative-id", []) or []
            ),
            "subject_keywords": self.serialize_json_list(
                record.get("subject", []) or []
            ),
            "_dq_warn": False,
            "_dq_error": False,
        }


class _CrossRefJournalBlock:
    """Extracts journal and ISSN information."""

    def extract(self, record: BronzeRecord) -> JsonDict:
        return {
            **extract_journal_info(record),
            **extract_issn_by_type(record),
            "journal_name_short": extract_first_string(
                record.get("short-container-title")
            ),
        }


class _CrossRefMetadataBlock:
    """Extracts page info, content domains, references, and citations."""

    def __init__(
        self,
        serialize_json: Callable[[object], ScalarValue],
        serialize_json_list: Callable[[Sequence[object] | None], str | None],
    ) -> None:
        self.serialize_json = serialize_json
        self.serialize_json_list = serialize_json_list

    def extract(self, record: BronzeRecord) -> JsonDict:
        content_domain = extract_content_domain(record)
        raw_references = extract_references(record)
        references = self.serialize_json(raw_references)

        return {
            **extract_page_info(record),
            "citations_received": record.get("is-referenced-by-count"),
            "citations_made": record.get("references-count"),
            "license_url": extract_license_url(record),
            "content_domain_domains": self.serialize_json_list(
                content_domain.get("content_domain_domains", [])
            ),
            "content_domain_crossmark_restriction": content_domain.get(
                "content_domain_crossmark_restriction"
            ),
            "references": references if isinstance(references, str) else None,
        }


class _CrossRefDateBlock:
    """Extracts and normalizes CrossRef date fields."""

    def __init__(
        self, validate_publication_year: Callable[[object], int | None]
    ) -> None:
        self.validate_publication_year = validate_publication_year

    def _extract_common_date(
        self,
        record: BronzeRecord,
    ) -> tuple[int | None, str | None]:
        dates = extract_dates(record)
        pub_date = dates.get("published_print") or dates.get("published_online")
        return _extract_crossref_publication_year_candidate(record), pub_date

    def extract(self, record: BronzeRecord) -> JsonDict:
        raw_year, publication_date = self._extract_common_date(record)
        dates = extract_dates(record)
        return {
            **dates,
            "published": extract_published_date(record),
            "publication_year": self.validate_publication_year(raw_year),
            "publication_date": publication_date,
        }


class _CrossRefAuthorBlock:
    """Extracts and hashes CrossRef author data."""

    def __init__(
        self,
        data_normalizer: DataNormalizationPort,
        hash_pii_value: Callable[[str | None], str | None],
        serialize_json: Callable[[object], ScalarValue],
        serialize_json_list: Callable[[Sequence[object] | None], str | None],
    ) -> None:
        self.data_normalizer = data_normalizer
        self.hash_pii_value = hash_pii_value
        self.serialize_json = serialize_json
        self.serialize_json_list = serialize_json_list

    def _hash_author_detail(self, author: JsonDict) -> JsonDict:
        hashed_author: JsonDict = {}
        for pii_field in ("given", "family", "name"):
            val = author.get(pii_field)
            hashed_author[pii_field] = (
                self.hash_pii_value(val) if isinstance(val, str) and val else None
            )
        hashed_author["orcid"] = author.get("orcid")
        hashed_author["authenticated_orcid"] = author.get("authenticated_orcid")
        hashed_author["sequence"] = author.get("sequence")

        affs = author.get("affiliations", [])
        hashed_author["affiliations"] = affs
        return hashed_author

    def _extract_affiliations(
        self,
        raw_author_details: list[JsonDict],
    ) -> list[str] | list[JsonDict] | None:
        affiliation_strings: list[str] = []
        affiliation_dicts: list[JsonDict] = []

        for author in raw_author_details:
            affs = author.get("affiliations", [])
            if isinstance(affs, list):
                for aff in affs:
                    if isinstance(aff, str):
                        affiliation_strings.append(aff)
                    elif isinstance(aff, dict):
                        affiliation_dicts.append(aff)

        if affiliation_dicts:
            return affiliation_dicts
        if affiliation_strings:
            return affiliation_strings
        return None

    def extract(self, record: BronzeRecord) -> JsonDict:
        raw_authors = extract_authors(record)
        authors_json = self.data_normalizer.normalize_author_list(raw_authors)
        author_keys = self.data_normalizer.normalize_author_keys(raw_authors)

        raw_author_details = extract_author_details(record)
        hashed_details = [self._hash_author_detail(a) for a in raw_author_details]
        affiliations_input = self._extract_affiliations(raw_author_details)

        author_details = self.serialize_json(hashed_details)
        author_orcids = extract_author_orcids(record)
        serialized_orcids = self.serialize_json_list(author_orcids)

        affiliations_json = self.data_normalizer.normalize_affiliations(
            affiliations_input
        )

        return {
            "authors": authors_json,
            "author_keys": author_keys,
            "author_orcids": serialized_orcids,
            "author_details": author_details
            if isinstance(author_details, str)
            else None,
            "affiliation_list": affiliations_json,
        }


__all__ = [
    "_CrossRefAuthorBlock",
    "_CrossRefCoreBlock",
    "_CrossRefDateBlock",
    "_CrossRefJournalBlock",
    "_CrossRefMetadataBlock",
]
