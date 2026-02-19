"""Identifier extraction from PubMed XML elements.

Handles extraction of DOI, PMC ID, PII, MID, and other article identifiers.
Supports complete ArticleIdList and ELocationID extraction for cross-referencing.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor
from bioetl.application.pipelines.pubmed.extractors.identifier_types import (
    AllArticleIds,
    ArticleIdentifiers,
    ELocationIds,
    NormalizedIdentifiers,
    RawIdentifiers,
)


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

    def _extract_from_elocation(
        self, article: Element, result: dict[str, str | None]
    ) -> None:
        """Extract identifiers from ELocationID elements."""
        for eloc in article.findall("ELocationID"):
            eid_type = eloc.get("EIdType")
            if not eid_type or not eloc.text:
                continue

            normalized = self._normalize_text(eloc.text)
            if not normalized:
                continue

            if eid_type == "doi":
                result["doi"] = normalized
            elif eid_type == "pii":
                result["pii"] = normalized

    def _extract_from_article_id_list(
        self, article_id_list: Element, result: dict[str, str | None]
    ) -> None:
        """Extract identifiers from ArticleIdList elements."""
        for aid in article_id_list.findall("ArticleId"):
            id_type = aid.get("IdType")
            if not id_type or not aid.text:
                continue

            normalized = self._normalize_text(aid.text)
            if not normalized:
                continue

            if id_type == "doi":
                if result["doi"] is None:
                    result["doi"] = normalized
            elif id_type == "pii":
                if result["pii"] is None:
                    result["pii"] = normalized
            elif id_type == "pmc":
                result["pmc_id"] = normalized
            elif id_type == "mid":
                result["mid"] = normalized
            elif id_type == "publisher-id":
                result["publisher_id"] = normalized

    @classmethod
    def extract_all_identifiers(cls, root: Element) -> dict[str, str | None]:
        """Extract all supported identifiers from PubMed XML in a single pass.

        Combines ELocationID and ArticleIdList extraction strategies.
        Priority: ELocationID > ArticleIdList for DOI and PII.

        Args:
            root: Root PubmedArticle element.

        Returns:
            Dictionary with keys: doi, pii, mid, publisher_id, pmc_id.
            Values are normalized strings or None.
        """
        extractor = cls()
        result: dict[str, str | None] = {
            "doi": None,
            "pii": None,
            "mid": None,
            "publisher_id": None,
            "pmc_id": None,
        }

        # 1. Scan ELocationID (higher priority for DOI/PII)
        article = root.find(".//Article")
        if article is not None:
            extractor._extract_from_elocation(article, result)

        # 2. Scan ArticleIdList (fallback for DOI/PII, primary for others)
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            extractor._extract_from_article_id_list(article_id_list, result)

        return result

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

    @classmethod
    def parse_all_article_ids(cls, root: Element) -> AllArticleIds:
        """Extract complete set of article identifiers from ArticleIdList.

        This method extracts all available identifiers from PubmedData/ArticleIdList,
        including less common ones like PII, MID, and publisher-specific IDs that
        are useful for cross-referencing with publisher databases.

        Args:
            root: Root PubmedArticle element.

        Returns:
            AllArticleIds dict with all available identifiers.
            The 'other_ids' field contains any ID types not explicitly mapped.
        """
        extractor = cls()
        result: AllArticleIds = {
            "pubmed": None,
            "doi": None,
            "pmc": None,
            "pii": None,
            "mid": None,
            "publisher_id": None,
            "pmcid": None,
            "medline": None,
            "other_ids": {},
        }

        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is None:
            return result

        # Map IdType values to our field names
        type_mapping = {
            "pubmed": "pubmed",
            "doi": "doi",
            "pmc": "pmc",
            "pii": "pii",
            "mid": "mid",
            "publisher-id": "publisher_id",
            "pmcid": "pmcid",
            "medline": "medline",
        }

        for aid in article_id_list.findall("ArticleId"):
            id_type = aid.get("IdType")
            if not id_type or not aid.text:
                continue

            normalized_value = extractor._normalize_text(aid.text)
            if not normalized_value:
                continue

            if id_type in type_mapping:
                result[type_mapping[id_type]] = normalized_value  # type: ignore[literal-required]
            else:
                # Store unknown ID types in other_ids
                result["other_ids"][id_type] = normalized_value

        return result

    @classmethod
    def extract_elocation_ids(cls, root: Element) -> ELocationIds:
        """Extract electronic location identifiers from ELocationID elements.

        ELocationID elements appear in Article and can contain DOI, PII,
        and other electronic identifiers used by publishers.

        Args:
            root: Root PubmedArticle element.

        Returns:
            ELocationIds dict with doi and pii if available.
        """
        extractor = cls()
        result: ELocationIds = {
            "doi": None,
            "pii": None,
        }

        article = root.find(".//Article")
        if article is None:
            return result

        for eloc in article.findall(".//ELocationID"):
            eid_type = eloc.get("EIdType")
            if not eid_type or not eloc.text:
                continue

            normalized_value = extractor._normalize_text(eloc.text)
            if not normalized_value:
                continue

            if eid_type == "doi":
                result["doi"] = normalized_value
            elif eid_type == "pii":
                result["pii"] = normalized_value

        return result

    @classmethod
    def extract_pii(cls, root: Element) -> str | None:
        """Extract Publisher Item Identifier (PII).

        Tries ELocationID first, then ArticleIdList.

        Args:
            root: Root PubmedArticle element.

        Returns:
            PII string or None.
        """
        extractor = cls()

        # Try ELocationID first
        article = root.find(".//Article")
        if article is not None:
            for eloc in article.findall(".//ELocationID"):
                if eloc.get("EIdType") == "pii" and eloc.text:
                    return extractor._normalize_text(eloc.text)

        # Fallback to ArticleIdList
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "pii" and aid.text:
                    return extractor._normalize_text(aid.text)

        return None

    @classmethod
    def extract_mid(cls, root: Element) -> str | None:
        """Extract Manuscript ID (MID) used in PMC submission.

        Args:
            root: Root PubmedArticle element.

        Returns:
            MID string or None.
        """
        extractor = cls()
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "mid" and aid.text:
                    return extractor._normalize_text(aid.text)
        return None

    @classmethod
    def extract_publisher_id(cls, root: Element) -> str | None:
        """Extract publisher-specific identifier.

        Args:
            root: Root PubmedArticle element.

        Returns:
            Publisher ID string or None.
        """
        extractor = cls()
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "publisher-id" and aid.text:
                    return extractor._normalize_text(aid.text)
        return None
