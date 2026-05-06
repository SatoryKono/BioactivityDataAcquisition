"""Declarative block implementations for PubMed publication pipeline."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET  # nosec B405
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, cast

from bioetl.application.pipelines.common.publication_issn import build_issn_fields
from bioetl.application.pipelines.pubmed._block_helpers import (
    build_authors_with_affiliations,
    extract_date_data,
    extract_journal_data,
    process_structured_affiliations,
)
from bioetl.application.pipelines.pubmed.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.pubmed.extractors.author import AuthorExtractor
from bioetl.application.pipelines.pubmed.extractors.classification import (
    ClassificationExtractor,
)
from bioetl.application.pipelines.pubmed.extractors.date import DateExtractor
from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)
from bioetl.application.pipelines.pubmed.xml_parser import get_text
from bioetl.domain.mapping.pubmed_publication import (
    build_pubmed_publication_type_fields,
)
from bioetl.domain.normalization import normalize_pmc_id
from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.domain.value_objects.publications import DOI, PubMedId

if TYPE_CHECKING:
    from bioetl.domain.ports import DataNormalizationPort, PiiHasherPort


class _PubMedXmlBlock:
    """Base helper for PubMed extraction blocks over cached XML roots."""

    def __init__(
        self,
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        self._root_resolver = root_resolver

    def _resolve_root(self) -> ET.Element | None:
        return self._root_resolver()

    def _resolve_article_context(
        self,
    ) -> tuple[ET.Element | None, ET.Element | None, ET.Element | None]:
        root = self._resolve_root()
        if root is None:
            return None, None, None
        return (
            root.find(".//Article"),
            root.find(".//MedlineCitation"),
            root.find(".//PubmedData"),
        )


class _PubMedIdentifierBlock(_PubMedXmlBlock):
    """Extract PubMed identifiers from cached XML root."""

    def __init__(
        self,
        *,
        data_normalizer: DataNormalizationPort,
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        super().__init__(root_resolver)
        self._data_normalizer = data_normalizer

    def extract(self, record: BronzeRecord) -> JsonDict:
        del record
        root = self._resolve_root()
        if root is None:
            return {"pmid": None}

        identifiers = IdentifierExtractor.extract_all_identifiers(root)
        raw_pmid = get_text(root.find(".//PMID"))
        pmid_vo = PubMedId.from_raw(raw_pmid)
        if root.find(".//Article") is None:
            return {"pmid": str(pmid_vo) if pmid_vo else None}

        doi_vo = DOI.from_raw(identifiers["doi"])
        return {
            "pmid": str(pmid_vo) if pmid_vo else None,
            "doi": str(doi_vo) if doi_vo else None,
            "pii": self._data_normalizer.normalize_to_string(identifiers["pii"]),
            "mid": self._data_normalizer.normalize_to_string(identifiers["mid"]),
            "publisher_id": self._data_normalizer.normalize_to_string(
                identifiers["publisher_id"]
            ),
            "pmc_id": normalize_pmc_id(identifiers["pmc_id"]),
        }


class _PubMedCoreBlock(_PubMedXmlBlock):
    """Extract core publication content and lineage metadata."""

    def __init__(
        self,
        *,
        data_normalizer: DataNormalizationPort,
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        super().__init__(root_resolver)
        self._data_normalizer = data_normalizer

    def extract(self, record: BronzeRecord) -> JsonDict:
        article, _, _ = self._resolve_article_context()
        if article is None:
            return {}

        return {
            "title": get_text(article.find(".//ArticleTitle")),
            "abstract": self._data_normalizer.strip_html_tags(
                AbstractExtractor.extract_abstract(article)
            ),
            "abstract_structured": AbstractExtractor.is_abstract_structured(article),
            "language": get_text(article.find(".//Language")),
            "_source": "pubmed",
            "citations_received": None,
            "is_oa": None,
            "_lookup_method": record.get("_lookup_method", "pmid"),
            "_original_id": record.get("_original_id"),
            "_dq_warn": False,
            "_dq_error": False,
        }


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

    def extract(self, _record: BronzeRecord) -> JsonDict:
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

    def extract(self, _record: BronzeRecord) -> JsonDict:
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


class _PubMedDateBlock(_PubMedXmlBlock):
    """Extract normalized publication dates from PubMed XML."""

    def __init__(
        self,
        *,
        date_extractor: DateExtractor,
        data_normalizer: DataNormalizationPort,
        validate_publication_year: Callable[[object], int | None],
        valid_date_patterns: Sequence[re.Pattern[str]],
        month_map: dict[str, int],
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        super().__init__(root_resolver)
        self._date_extractor = date_extractor
        self._data_normalizer = data_normalizer
        self._validate_publication_year = validate_publication_year
        self._valid_date_patterns = tuple(valid_date_patterns)
        self._month_map = month_map

    def extract(self, _record: BronzeRecord) -> JsonDict:
        article, medline, pubmed_data = self._resolve_article_context()
        if article is None:
            return {}
        return extract_date_data(
            article=article,
            pubmed_data=pubmed_data,
            medline=medline,
            date_extractor=self._date_extractor,
            data_normalizer=self._data_normalizer,
            validate_publication_year=self._validate_publication_year,
            valid_date_patterns=self._valid_date_patterns,
            month_map=self._month_map,
        )


class _PubMedClassificationBlock(_PubMedXmlBlock):
    """Extract PubMed classification payloads."""

    def __init__(
        self,
        *,
        serialize_json_list: Callable[[Sequence[object] | None], str | None],
        classify_publication_types: Callable[[list[str]], dict[str, str | None]],
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        super().__init__(root_resolver)
        self._serialize_json_list = serialize_json_list
        self._classify_publication_types = classify_publication_types

    def extract(self, _record: BronzeRecord) -> JsonDict:
        article, medline, _ = self._resolve_article_context()
        if article is None:
            return {}

        publication_types = ClassificationExtractor.parse_publication_types(article)
        subject_keywords = ClassificationExtractor.parse_keywords(medline)
        subject_mesh = ClassificationExtractor.parse_mesh_terms(medline)
        chemicals = ClassificationExtractor.parse_chemicals(medline)
        return {
            "publication_types": self._serialize_json_list(publication_types),
            "subject_keywords": self._serialize_json_list(subject_keywords),
            "keyword_count": len(subject_keywords) if subject_keywords else 0,
            "subject_mesh": self._serialize_json_list(subject_mesh),
            "mesh_heading_count": len(subject_mesh) if subject_mesh else 0,
            "chemicals": self._serialize_json_list(chemicals),
            "chemical_count": len(chemicals) if chemicals else 0,
            "gene_symbols": self._serialize_json_list(
                ClassificationExtractor.parse_gene_symbols(medline)
            ),
            "databanks": self._serialize_json_list(
                ClassificationExtractor.parse_databanks(medline)
            ),
            **build_pubmed_publication_type_fields(
                publication_types,
                classification=self._classify_publication_types(publication_types),
            ),
        }


class _PubMedMetricsBlock(_PubMedXmlBlock):
    """Extract simple count-based PubMed metrics."""

    def extract(self, _record: BronzeRecord) -> JsonDict:
        article, _, pubmed_data = self._resolve_article_context()
        if article is None:
            return {}

        grant_list = article.find(".//GrantList")
        reference_list = (
            pubmed_data.find("ReferenceList") if pubmed_data is not None else None
        )
        return {
            "grant_count": len(grant_list.findall("Grant"))
            if grant_list is not None
            else 0,
            "citations_made": len(reference_list.findall(".//Reference"))
            if reference_list is not None
            else 0,
        }
