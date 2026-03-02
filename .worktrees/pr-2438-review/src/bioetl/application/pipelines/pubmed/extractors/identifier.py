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

__all__ = [
    "AllArticleIds",
    "ArticleIdentifiers",
    "ELocationIds",
    "IdentifierExtractor",
    "NormalizedIdentifiers",
    "RawIdentifiers",
]


class IdentifierExtractor(BaseFieldExtractor):
    """Extractor for article identifiers from PubMed XML.

    Handles:
    - DOI from ELocationID or ArticleIdList
    - PMC ID from ArticleIdList
    - PMID (via get_text utility)
    """

    def extract(self, element: Element | None) -> RawIdentifiers | None:
        """Extract identifiers from XML using the optimized single-pass method.

        Args:
            element: Root PubmedArticle element.

        Returns:
            Dict with raw doi and pmc_id, or None.
        """
        if element is None:
            return None

        # Use the optimized single-pass extractor
        all_ids = self.extract_all_identifiers(element)
        return RawIdentifiers(
            doi=all_ids["doi"],
            pmc_id=all_ids["pmc_id"],
        )

    def normalize(self, raw_value: RawIdentifiers) -> NormalizedIdentifiers:
        """Normalize identifiers.

        Args:
            raw_value: Raw identifiers dict.

        Returns:
            Normalized identifiers dict.
        """
        return NormalizedIdentifiers(
            doi=self._normalize_text(raw_value.get("doi")),
            pmc_id=self._normalize_text(raw_value.get("pmc_id")),
        )

    def _normalize_text(self, text: str | None) -> str | None:
        """Normalize text by stripping whitespace."""
        return text.strip() if text else None

    @classmethod
    def extract_doi(cls, root: Element) -> str | None:
        """Extract DOI from ArticleIdList or ELocationID.

        Delegates to extract_all_identifiers for efficient extraction.

        Args:
            root: Root PubmedArticle element.

        Returns:
            DOI string or None.
        """
        return cls.extract_all_identifiers(root)["doi"]

    @classmethod
    def extract_pmc_id(cls, root: Element) -> str | None:
        """Extract PubMed Central ID from ArticleIdList.

        Delegates to extract_all_identifiers.

        Args:
            root: Root PubmedArticle element.

        Returns:
            PMC ID string or None.
        """
        return cls.extract_all_identifiers(root)["pmc_id"]

    @classmethod
    def extract_all_identifiers(cls, root: Element) -> dict[str, str | None]:
        """Extract all relevant identifiers in a single pass.

        Optimized to scan ELocationID (for DOI/PII) and ArticleIdList (for others)
        only once each, reducing XML traversal overhead compared to individual calls.

        Returns:
            Dictionary with keys: doi, pii, pmc_id, mid, publisher_id.
            Values are normalized strings (stripped) or None.
        """
        extractor = cls()
        result: dict[str, str | None] = {
            "doi": None,
            "pii": None,
            "pmc_id": None,
            "mid": None,
            "publisher_id": None,
        }

        # 1. Scan ELocationID (Priority for DOI, PII)
        extractor._scan_elocation_ids(root.find(".//Article"), result)

        # 2. Scan ArticleIdList (Fallback for DOI/PII, Primary for others)
        extractor._scan_article_id_list(root.find(".//ArticleIdList"), result)

        return result

    def _scan_elocation_ids(
        self, article: Element | None, result: dict[str, str | None]
    ) -> None:
        """Scan ELocationID elements for identifiers.

        Updates result dict in-place.
        """
        if article is None:
            return

        for eloc in article.findall("ELocationID"):
            eid_type = eloc.get("EIdType")
            if not eid_type or not eloc.text:
                continue

            normalized = self._normalize_text(eloc.text)
            if not normalized:
                continue

            if eid_type == "doi" and result["doi"] is None:
                result["doi"] = normalized
            elif eid_type == "pii" and result["pii"] is None:
                result["pii"] = normalized

    def _scan_article_id_list(
        self, article_id_list: Element | None, result: dict[str, str | None]
    ) -> None:
        """Scan ArticleIdList elements for identifiers."""
        if article_id_list is None:
            return

        for aid in article_id_list.findall("ArticleId"):
            self._process_article_id(aid, result)

    def _process_article_id(self, aid: Element, result: dict[str, str | None]) -> None:
        """Process a single ArticleId element."""
        id_type = aid.get("IdType")
        if not id_type or not aid.text:
            return

        normalized = self._normalize_text(aid.text)
        if not normalized:
            return

        # Mapping of XML IdType to result key
        # Note: "pmc" maps to "pmc_id"
        key_map = {
            "doi": "doi",
            "pii": "pii",
            "pmc": "pmc_id",
            "mid": "mid",
            "publisher-id": "publisher_id",
        }

        if (key := key_map.get(id_type)) and result[key] is None:
            result[key] = normalized

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

        Args:
            root: Root PubmedArticle element.

        Returns:
            PII string or None.
        """
        return cls.extract_all_identifiers(root)["pii"]

    @classmethod
    def extract_mid(cls, root: Element) -> str | None:
        """Extract Manuscript ID (MID) used in PMC submission.

        Args:
            root: Root PubmedArticle element.

        Returns:
            MID string or None.
        """
        return cls.extract_all_identifiers(root)["mid"]

    @classmethod
    def extract_publisher_id(cls, root: Element) -> str | None:
        """Extract publisher-specific identifier.

        Args:
            root: Root PubmedArticle element.

        Returns:
            Publisher ID string or None.
        """
        return cls.extract_all_identifiers(root)["publisher_id"]
