"""Author and journal block helpers for PubMed publication pipeline."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, cast

from bioetl.application.pipelines.common.publication_issn import build_issn_fields
from bioetl.application.pipelines.pubmed._block_definitions_base import _PubMedXmlBlock
from bioetl.application.pipelines.pubmed._block_helpers import (
    build_authors_with_affiliations,
    extract_journal_data,
    process_structured_affiliations,
)
from bioetl.application.pipelines.pubmed.extractors.author import AuthorExtractor
from bioetl.application.pipelines.pubmed.xml_parser import get_text
from bioetl.domain.types import BronzeRecord, JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import DataNormalizationPort, PiiHasherPort


class _PubMedAuthorBlock(_PubMedXmlBlock):
    """Extract author and affiliation fields from PubMed XML."""

    def __init__(
        self,
        *,
        author_extractor: AuthorExtractor,
        data_normalizer: DataNormalizationPort,
        pii_hasher: PiiHasherPort | None,
        serialize_json_list: Callable[[Sequence[object] | None], str | None],
        normalize_author_list: Callable[
            [list[str] | list[JsonDict] | str | None], str | None
        ],
        normalize_author_keys: Callable[
            [list[str] | list[JsonDict] | str | None], str | None
        ],
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        super().__init__(root_resolver)
        self._author_extractor = author_extractor
        self._data_normalizer = data_normalizer
        self._pii_hasher = pii_hasher
        self._serialize_json_list = serialize_json_list
        self._normalize_author_list = normalize_author_list
        self._normalize_author_keys = normalize_author_keys

    def extract(self, record: BronzeRecord) -> JsonDict:
        del record
        article, _, _ = self._resolve_article_context()
        if article is None:
            return {}

        raw_authors = self._author_extractor.extract(article) or []
        author_names = self._author_extractor.normalize(raw_authors)
        authors_with_affiliations = build_authors_with_affiliations(
            raw_authors,
            self._pii_hasher,
        )

        affiliation_strings = self._data_normalizer.extract_affiliations_from_authors(
            cast("list[JsonDict]", raw_authors)
        )
        affiliation_list = (
            self._data_normalizer.normalize_affiliations(affiliation_strings)
            if affiliation_strings
            else None
        )

        structured_affiliations = process_structured_affiliations(
            self._author_extractor.parse_structured_affiliations(article),
            self._pii_hasher,
        )
        authors_json = self._normalize_author_list(author_names)

        return {
            "authors": authors_json,
            "author_keys": self._normalize_author_keys(author_names),
            "authors_with_affiliations": self._serialize_json_list(
                authors_with_affiliations
            )
            if authors_with_affiliations
            else None,
            "affiliation_list": affiliation_list,
            "affiliation_structured": self._serialize_json_list(
                structured_affiliations
            ),
            "author_count": len(author_names),
        }


class _PubMedJournalBlock(_PubMedXmlBlock):
    """Extract journal and Medline metadata fields."""

    def __init__(
        self,
        *,
        serialize_json_list: Callable[[Sequence[object] | None], str | None],
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        super().__init__(root_resolver)
        self._serialize_json_list = serialize_json_list

    def _build_medline_fields(self, medline: ET.Element | None) -> JsonDict:
        if medline is None:
            return {
                "nlm_unique_id": None,
                "citation_subset": None,
                "country": None,
            }

        medline_info = medline.find("MedlineJournalInfo")
        citation_subsets = [
            get_text(subset) for subset in medline.findall("CitationSubset")
        ]
        return {
            "nlm_unique_id": (
                get_text(medline_info.find("NlmUniqueID"))
                if medline_info is not None
                else None
            ),
            "citation_subset": ",".join(subset for subset in citation_subsets if subset)
            or None,
            "country": get_text(medline.find(".//MedlineJournalInfo/Country")),
        }

    def _resolve_publication_status(
        self,
        pubmed_data: ET.Element | None,
    ) -> str | None:
        if pubmed_data is None:
            return None
        return get_text(pubmed_data.find("PublicationStatus"))

    def extract(self, record: BronzeRecord) -> JsonDict:
        del record
        article, medline, pubmed_data = self._resolve_article_context()
        if article is None:
            return {}

        journal_data = extract_journal_data(article)
        return {
            **journal_data,
            **build_issn_fields(
                journal_data.get("issn"),
                serialize_json_list=self._serialize_json_list,
            ),
            **self._build_medline_fields(medline),
            "publication_status": self._resolve_publication_status(pubmed_data),
        }


__all__ = ["_PubMedAuthorBlock", "_PubMedJournalBlock"]
