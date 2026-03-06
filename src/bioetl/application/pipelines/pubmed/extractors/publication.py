"""PubMed publication extraction orchestration helpers."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, cast

from bioetl.application.pipelines.pubmed.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.pubmed.extractors.author import (
    AuthorExtractor,
    RawAuthor,
)
from bioetl.application.pipelines.pubmed.extractors.classification import (
    ClassificationExtractor,
)
from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)
from bioetl.application.pipelines.pubmed.xml_parser import get_text
from bioetl.domain.mapping.pubmed_publication import (
    build_pubmed_publication_type_fields,
)
from bioetl.domain.normalization import normalize_pmc_id
from bioetl.domain.types import GoldRecord, JsonDict
from bioetl.domain.value_objects import DOI, PubMedId

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from bioetl.domain.ports import DataNormalizationPort
    from bioetl.domain.types import BronzeRecord

__all__ = [
    "PubMedAuthorBlockExtractor",
    "PubMedBusinessDataExtractor",
]


class PubMedAuthorBlockExtractor:
    """Extract and normalize PubMed author-related fields."""

    @staticmethod
    def extract(
        *,
        article: ET.Element,
        raw_author_data: list[RawAuthor],
        data_normalizer: DataNormalizationPort,
        author_extractor: AuthorExtractor,
        normalize_author_list: Callable[
            [list[str] | list[JsonDict] | str | None], str | None
        ],
        normalize_author_keys: Callable[
            [list[str] | list[JsonDict] | str | None], str | None
        ],
        serialize_json_list: Callable[[Sequence[object] | None], str | None],
        build_authors_with_affiliations: Callable[[list[RawAuthor]], list[JsonDict]],
        process_structured_affiliations: Callable[[list[JsonDict]], list[JsonDict]],
    ) -> JsonDict:  # Any: untyped PubMed XML/JSON values
        """Extract author, affiliation, and structured-affiliation fields."""
        author_names = (
            author_extractor.normalize(raw_author_data) if raw_author_data else []
        )

        authors_json = normalize_author_list(author_names)
        author_keys = normalize_author_keys(author_names)

        authors_with_affiliations = build_authors_with_affiliations(raw_author_data)

        affiliation_strings = data_normalizer.extract_affiliations_from_authors(
            cast(
                "list[JsonDict]",  # Any: transformer record has heterogeneous values
                raw_author_data,  # Any: RawAuthor is TypedDict-like payload
            )
        )
        affiliation_list_json = (
            data_normalizer.normalize_affiliations(affiliation_strings)
            if affiliation_strings
            else None
        )

        structured_affs = author_extractor.parse_structured_affiliations(article)
        processed = process_structured_affiliations(
            cast(
                "list[JsonDict]",  # Any: structured affiliations are dict-like payloads
                structured_affs,
            )
        )

        author_count = len(json.loads(authors_json)) if authors_json else 0
        return {
            "authors": authors_json,
            "author_keys": author_keys,
            "authors_with_affiliations": (
                serialize_json_list(authors_with_affiliations)
                if authors_with_affiliations
                else None
            ),
            "affiliation_list": affiliation_list_json,
            "affiliation_structured": serialize_json_list(processed),
            "author_count": author_count,
        }


class PubMedBusinessDataExtractor:
    """Extract PubMed business fields from parsed XML."""

    @staticmethod
    def _extract_identifiers(
        *,
        root: ET.Element,
        data_normalizer: DataNormalizationPort,
    ) -> JsonDict:  # Any: untyped PubMed XML/JSON values
        ids = IdentifierExtractor.extract_all_identifiers(root)

        raw_pmid = get_text(root.find(".//PMID"))
        pmid_vo = PubMedId.from_raw(raw_pmid)

        raw_doi = ids["doi"]
        doi_vo = DOI.from_raw(raw_doi)

        return {
            "pmid": str(pmid_vo) if pmid_vo else None,
            "doi": str(doi_vo) if doi_vo else None,
            "pii": data_normalizer.normalize_to_string(ids["pii"]),
            "mid": data_normalizer.normalize_to_string(ids["mid"]),
            "publisher_id": data_normalizer.normalize_to_string(ids["publisher_id"]),
            "pmc_id": normalize_pmc_id(ids["pmc_id"]),
        }

    @staticmethod
    def _extract_publication_status(pubmed_data: ET.Element | None) -> str | None:
        if pubmed_data is None:
            return None
        pub_status_elem = pubmed_data.find("PublicationStatus")
        return get_text(pub_status_elem) if pub_status_elem is not None else None

    @classmethod
    def _extract_medline_metadata(
        cls,
        *,
        medline: ET.Element | None,
        pubmed_data: ET.Element | None,
    ) -> JsonDict:  # Any: untyped PubMed XML/JSON values
        medline_info = medline.find("MedlineJournalInfo") if medline else None
        citation_subsets = (
            [get_text(cs) for cs in medline.findall("CitationSubset")]
            if medline
            else []
        )
        pub_status = cls._extract_publication_status(pubmed_data)
        return {
            "nlm_unique_id": (
                get_text(medline_info.find("NlmUniqueID"))
                if medline_info is not None
                else None
            ),
            "citation_subset": (
                ",".join(cs for cs in citation_subsets if cs)
                if citation_subsets
                else None
            ),
            "publication_status": pub_status,
            "country": (
                get_text(medline.find(".//MedlineJournalInfo/Country"))
                if medline
                else None
            ),
        }

    @staticmethod
    def _extract_counts(
        *,
        article: ET.Element,
        pubmed_data: ET.Element | None,
    ) -> dict[str, int]:
        grant_list = article.find(".//GrantList")
        grant_count = len(grant_list.findall("Grant")) if grant_list is not None else 0
        ref_list = (
            pubmed_data.find("ReferenceList") if pubmed_data is not None else None
        )
        reference_count = (
            len(ref_list.findall(".//Reference")) if ref_list is not None else 0
        )
        return {"grant_count": grant_count, "citations_made": reference_count}

    @staticmethod
    def _extract_classification_data(
        *,
        article: ET.Element,
        medline: ET.Element | None,
        serialize_json_list: Callable[[Sequence[object] | None], str | None],
    ) -> tuple[list[str], JsonDict]:  # Any: untyped PubMed XML/JSON values
        publication_types = ClassificationExtractor.parse_publication_types(article)
        subject_keywords = ClassificationExtractor.parse_keywords(medline)
        subject_mesh = ClassificationExtractor.parse_mesh_terms(medline)
        chemicals = ClassificationExtractor.parse_chemicals(medline)
        payload: JsonDict = {
            "publication_types": serialize_json_list(publication_types),
            "publication_type_list": serialize_json_list(publication_types),
            "subject_keywords": serialize_json_list(subject_keywords),
            "keyword_count": len(subject_keywords) if subject_keywords else 0,
            "subject_mesh": serialize_json_list(subject_mesh),
            "mesh_heading_count": len(subject_mesh) if subject_mesh else 0,
            "chemicals": serialize_json_list(chemicals),
            "chemical_count": len(chemicals) if chemicals else 0,
            "gene_symbols": serialize_json_list(
                ClassificationExtractor.parse_gene_symbols(medline)
            ),
            "databanks": serialize_json_list(
                ClassificationExtractor.parse_databanks(medline)
            ),
        }
        return publication_types, payload

    @classmethod
    def extract(
        cls,
        *,
        record: BronzeRecord,
        root: ET.Element,
        data_normalizer: DataNormalizationPort,
        author_extractor: AuthorExtractor,
        serialize_json_list: Callable[[Sequence[object] | None], str | None],
        extract_author_block: Callable[[ET.Element, list[RawAuthor]], JsonDict],
        extract_journal_data: Callable[[ET.Element], dict[str, object]],
        extract_date_data: Callable[
            [ET.Element, ET.Element | None, ET.Element | None], dict[str, object]
        ],
        classify_publication_types: Callable[[list[str]], dict[str, str | None]],
    ) -> GoldRecord:
        """Extract full PubMed business payload from parsed XML."""
        identifiers = cls._extract_identifiers(
            root=root, data_normalizer=data_normalizer
        )

        article = root.find(".//Article")
        if article is None:
            return {"pmid": identifiers["pmid"]}

        medline = root.find(".//MedlineCitation")
        pubmed_data = root.find(".//PubmedData")
        raw_author_data = author_extractor.extract(article) or []

        publication_types, classification_payload = cls._extract_classification_data(
            article=article,
            medline=medline,
            serialize_json_list=serialize_json_list,
        )
        publication_type_fields = build_pubmed_publication_type_fields(
            publication_types,
            classification=classify_publication_types(publication_types),
        )

        return {
            **identifiers,
            "title": get_text(article.find(".//ArticleTitle")),
            "abstract": data_normalizer.strip_html_tags(
                AbstractExtractor.extract_abstract(article)
            ),
            "abstract_structured": AbstractExtractor.is_abstract_structured(article),
            **extract_author_block(article, raw_author_data),
            **extract_journal_data(article),
            **extract_date_data(article, pubmed_data, medline),
            **classification_payload,
            **cls._extract_medline_metadata(medline=medline, pubmed_data=pubmed_data),
            **cls._extract_counts(article=article, pubmed_data=pubmed_data),
            "language": get_text(article.find(".//Language")),
            "_source": "pubmed",
            **publication_type_fields,
            "citations_received": None,
            "is_oa": None,
            "_lookup_method": record.get("_lookup_method", "pmid"),
            "_original_id": record.get("_original_id"),
            "_dq_warn": False,
            "_dq_error": False,
        }
