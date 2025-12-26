"""Identifier extraction from PubMed XML elements.

Handles extraction of DOI, PMC ID, and other article identifiers.
"""

from __future__ import annotations

from typing import TypedDict
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor


class RawIdentifiers(TypedDict):
    """Raw identifier data before normalization."""

    doi: str | None
    pmc_id: str | None


class NormalizedIdentifiers(TypedDict):
    """Normalized identifier data."""

    doi: str | None
    pmc_id: str | None


class IdentifierExtractor(BaseFieldExtractor):
    """Extractor for article identifiers from PubMed XML.

    Handles:
    - DOI from ELocationID or ArticleIdList
    - PMC ID from ArticleIdList
    - PMID (via get_text utility)
    """

    def extract(self, element: Element | None) -> RawIdentifiers | None:
        """Извлечь сырые идентификаторы из XML.

        Args:
            element: Root PubmedArticle element.

        Returns:
            Dict with raw doi and pmc_id, or None.
        """
        if element is None:
            return None

        return RawIdentifiers(
            doi=self._extract_doi_raw(element),
            pmc_id=self._extract_pmc_raw(element),
        )

    def normalize(self, raw_value: RawIdentifiers) -> NormalizedIdentifiers:
        """Нормализовать идентификаторы.

        Args:
            raw_value: Raw identifiers dict.

        Returns:
            Normalized identifiers dict.
        """
        return NormalizedIdentifiers(
            doi=self._normalize_text(raw_value.get("doi")),
            pmc_id=self._normalize_text(raw_value.get("pmc_id")),
        )

    def _extract_doi_raw(self, root: Element) -> str | None:
        """Extract raw DOI from ArticleIdList or ELocationID."""
        article = root.find(".//Article")
        if article is None:
            return None

        # Try ELocationID first
        for eloc in article.findall(".//ELocationID"):
            if eloc.get("EIdType") == "doi" and eloc.text:
                return eloc.text

        # Fallback to ArticleIdList
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "doi" and aid.text:
                    return aid.text

        return None

    def _extract_pmc_raw(self, root: Element) -> str | None:
        """Extract raw PMC ID from ArticleIdList."""
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "pmc" and aid.text:
                    return aid.text
        return None

    def _normalize_text(self, text: str | None) -> str | None:
        """Normalize text by stripping whitespace."""
        return text.strip() if text else None

    @classmethod
    def extract_doi(cls, root: Element) -> str | None:
        """Extract DOI from ArticleIdList or ELocationID.

        First tries ELocationID with EIdType="doi", then falls back
        to ArticleIdList with IdType="doi".

        Args:
            root: Root PubmedArticle element.

        Returns:
            DOI string or None.
        """
        extractor = cls()
        raw = extractor._extract_doi_raw(root)
        return extractor._normalize_text(raw)

    @classmethod
    def extract_pmc_id(cls, root: Element) -> str | None:
        """Extract PubMed Central ID from ArticleIdList.

        Args:
            root: Root PubmedArticle element.

        Returns:
            PMC ID string or None.
        """
        extractor = cls()
        raw = extractor._extract_pmc_raw(root)
        return extractor._normalize_text(raw)
