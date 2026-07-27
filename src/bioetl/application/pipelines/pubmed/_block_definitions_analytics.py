"""Date and classification blocks for PubMed publication pipeline."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405
from collections.abc import Callable, Sequence

from bioetl.application.pipelines.pubmed._block_definitions_base import _PubMedXmlBlock
from bioetl.application.pipelines.pubmed.extractors.classification import (
    ClassificationExtractor,
)
from bioetl.domain.mapping.pubmed_publication import (
    build_pubmed_publication_type_fields,
)
from bioetl.domain.types import BronzeRecord, JsonDict


class _PubMedDateBlock(_PubMedXmlBlock):
    """Extract normalized publication dates from PubMed XML."""

    def __init__(
        self,
        *,
        extract_date_data: Callable[
            [ET.Element, ET.Element | None, ET.Element | None],
            dict[str, object],
        ],
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        super().__init__(root_resolver)
        self._extract_date_data = extract_date_data

    def extract(self, record: BronzeRecord) -> JsonDict:
        del record
        article, medline, pubmed_data = self._resolve_article_context()
        if article is None:
            return {}
        return self._extract_date_data(article, pubmed_data, medline)


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

    def extract(self, record: BronzeRecord) -> JsonDict:
        del record
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

    def extract(self, record: BronzeRecord) -> JsonDict:
        del record
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


__all__ = [
    "_PubMedClassificationBlock",
    "_PubMedDateBlock",
    "_PubMedMetricsBlock",
]
