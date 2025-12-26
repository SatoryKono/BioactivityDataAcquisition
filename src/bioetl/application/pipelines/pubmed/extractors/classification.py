"""Classification extraction from PubMed XML elements.

Handles extraction of keywords, MeSH terms, and publication types.
"""

from __future__ import annotations

from typing import TypedDict
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor


class RawClassification(TypedDict):
    """Raw classification data before normalization."""

    keywords: list[str | None]
    mesh_terms: list[str | None]
    publication_types: list[str | None]


class NormalizedClassification(TypedDict):
    """Normalized classification data."""

    keywords: list[str]
    mesh_terms: list[str]
    publication_types: list[str]


class ClassificationExtractor(BaseFieldExtractor):
    """Extractor for classification data from PubMed XML.

    Handles:
    - Keywords from KeywordList
    - MeSH terms from MeshHeadingList
    - Publication types from PublicationTypeList
    """

    def extract(self, element: Element | None) -> RawClassification | None:
        """Извлечь сырые данные классификации из XML.

        Args:
            element: Root PubmedArticle element.

        Returns:
            Dict with raw keywords, mesh_terms, and publication_types.
        """
        if element is None:
            return None

        medline = element.find(".//MedlineCitation")
        article = element.find(".//Article")

        return RawClassification(
            keywords=self._extract_keywords_raw(medline),
            mesh_terms=self._extract_mesh_raw(medline),
            publication_types=self._extract_pub_types_raw(article),
        )

    def normalize(self, raw_value: RawClassification) -> NormalizedClassification:
        """Нормализовать данные классификации.

        Args:
            raw_value: Raw classification dict.

        Returns:
            Normalized classification dict with cleaned lists.
        """
        return NormalizedClassification(
            keywords=self._normalize_list(raw_value["keywords"]),
            mesh_terms=self._normalize_list(raw_value["mesh_terms"]),
            publication_types=self._normalize_list(raw_value["publication_types"]),
        )

    def _extract_keywords_raw(self, medline: Element | None) -> list[str | None]:
        """Extract raw keyword texts."""
        if medline is None:
            return []
        keyword_list = medline.find(".//KeywordList")
        if keyword_list is None:
            return []
        return [kw.text for kw in keyword_list.findall("Keyword")]

    def _extract_mesh_raw(self, medline: Element | None) -> list[str | None]:
        """Extract raw MeSH descriptor texts."""
        if medline is None:
            return []
        mesh_list = medline.find(".//MeshHeadingList")
        if mesh_list is None:
            return []
        texts = []
        for heading in mesh_list.findall("MeshHeading"):
            descriptor = heading.find("DescriptorName")
            if descriptor is not None:
                texts.append(descriptor.text)
        return texts

    def _extract_pub_types_raw(self, article: Element | None) -> list[str | None]:
        """Extract raw publication type texts."""
        if article is None:
            return []
        type_list = article.find(".//PublicationTypeList")
        if type_list is None:
            return []
        return [pt.text for pt in type_list.findall("PublicationType")]

    def _normalize_list(self, raw_list: list[str | None]) -> list[str]:
        """Normalize a list by stripping and filtering empty values."""
        return [text.strip() for text in raw_list if text and text.strip()]

    @classmethod
    def parse_keywords(cls, medline_citation: Element | None) -> list[str]:
        """Extract keywords from KeywordList.

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of keyword strings.
        """
        extractor = cls()
        raw = extractor._extract_keywords_raw(medline_citation)
        return extractor._normalize_list(raw)

    @classmethod
    def parse_mesh_terms(cls, medline_citation: Element | None) -> list[str]:
        """Extract MeSH terms from MeshHeadingList.

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of MeSH descriptor names.
        """
        extractor = cls()
        raw = extractor._extract_mesh_raw(medline_citation)
        return extractor._normalize_list(raw)

    @classmethod
    def parse_publication_types(cls, article_node: Element) -> list[str]:
        """Extract publication types from PublicationTypeList.

        Args:
            article_node: The Article element.

        Returns:
            List of publication type strings.
        """
        extractor = cls()
        raw = extractor._extract_pub_types_raw(article_node)
        return extractor._normalize_list(raw)
