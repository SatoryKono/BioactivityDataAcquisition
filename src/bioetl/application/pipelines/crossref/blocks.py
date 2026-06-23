"""Private declarative extraction helpers for the CrossRef pipeline."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from bioetl.application.core.base_transformer_helpers_mixin import ScalarValue
from bioetl.application.pipelines.crossref._business_data_builder import (
    build_crossref_author_block_fields,
    build_crossref_core_block_fields,
    extract_publication_year_candidate,
)
from bioetl.application.pipelines.crossref.extractors import (
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
        return build_crossref_core_block_fields(
            record=record,
            doi=doi,
            classify_publication_type=self.classify_pub_type,
            serialize_json_list=self.serialize_json_list,
        )


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
        references_raw_json = self.serialize_json(raw_references)
        references_canonical_json = self.serialize_json(raw_references)

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
            "references": (
                references_canonical_json
                if isinstance(references_canonical_json, str)
                else None
            ),
            "references_raw_json": (
                references_raw_json if isinstance(references_raw_json, str) else None
            ),
            "references_canonical_json": (
                references_canonical_json
                if isinstance(references_canonical_json, str)
                else None
            ),
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
        return extract_publication_year_candidate(record), pub_date

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

    def extract(self, record: BronzeRecord) -> JsonDict:
        return build_crossref_author_block_fields(
            record,
            data_normalizer=self.data_normalizer,
            hash_pii_value=self.hash_pii_value,
            serialize_json=self.serialize_json,
            serialize_json_list=self.serialize_json_list,
        )


__all__ = [
    "_CrossRefAuthorBlock",
    "_CrossRefCoreBlock",
    "_CrossRefDateBlock",
    "_CrossRefJournalBlock",
    "_CrossRefMetadataBlock",
]
