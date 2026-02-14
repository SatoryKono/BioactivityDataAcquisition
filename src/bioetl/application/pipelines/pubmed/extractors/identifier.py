"""Identifier extraction from PubMed XML elements.

Handles extraction of DOI, PMC ID, PII, MID, and other article identifiers.
Supports complete ArticleIdList and ELocationID extraction for cross-referencing.
"""

from __future__ import annotations

from typing import TypedDict
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor


class ArticleIdentifiers(TypedDict):
    """Identifier data container (raw or normalized)."""

    doi: str | None
    pmc_id: str | None


# Aliases for clarity in extractor API
RawIdentifiers = ArticleIdentifiers
NormalizedIdentifiers = ArticleIdentifiers


class AllArticleIds(TypedDict, total=False):
    """Complete set of article identifiers from PubMed.

    ArticleIdList can contain various ID types:
    - pubmed: PubMed ID
    - doi: Digital Object Identifier
    - pmc: PubMed Central ID
    - pii: Publisher Item Identifier
    - mid: Manuscript ID (PMC submission)
    - publisher-id: Publisher-specific identifier
    - pmcid: Alternative PMC ID format
    - medline: MEDLINE unique ID
    """

    pubmed: str | None
    doi: str | None
    pmc: str | None
    pii: str | None
    mid: str | None
    publisher_id: str | None
    pmcid: str | None
    medline: str | None
    other_ids: dict[str, str]  # Any other ID types encountered


class ELocationIds(TypedDict, total=False):
    """Electronic location identifiers from ELocationID elements.

    ELocationID provides additional identifiers like:
    - doi: Digital Object Identifier
    - pii: Publisher Item Identifier
    """

    doi: str | None
    pii: str | None


class IdentifierExtractor(BaseFieldExtractor):
    """Extractor for article identifiers from PubMed XML.

    Handles:
    - DOI from ELocationID or ArticleIdList
    - PMC ID from ArticleIdList
    - PMID (via get_text utility)
    """

    def extract(self, element: Element | None) -> None:
        """Deprecated: Use extract_all_identifiers instead.

        Required by BaseFieldExtractor ABC.
        """
        return None

    def normalize(self, raw_value: Any) -> None:
        """Deprecated: Use extract_all_identifiers instead.

        Required by BaseFieldExtractor ABC.
        """
        return None

    @staticmethod
    def _normalize_text(text: str | None) -> str | None:
        """Normalize text by stripping whitespace."""
        return text.strip() if text else None

    @classmethod
    def extract_all_identifiers(cls, root: Element) -> dict[str, str | None]:
        """Extract all article identifiers in a single pass.

        Optimized to traverse the XML structure only once for multiple identifiers,
        reducing overhead compared to calling individual extract methods.

        Args:
            root: Root PubmedArticle element.

        Returns:
            Dictionary with normalized values for:
            - doi
            - pmc_id
            - pii
            - mid
            - publisher_id
        """
        ids: dict[str, str | None] = {
            "doi": None,
            "pmc_id": None,
            "pii": None,
            "mid": None,
            "publisher_id": None,
        }

        # 1. Check ELocationID (higher priority for DOI/PII)
        cls._process_elocation_ids(root, ids)

        # 2. Check ArticleIdList (fallback for DOI/PII, primary for others)
        cls._process_article_id_list(root, ids)

        return ids

    @classmethod
    def _process_elocation_ids(
        cls, root: Element, ids: dict[str, str | None]
    ) -> None:
        """Process ELocationID elements to populate identifiers.

        Modifies the ids dictionary in-place.
        """
        # XML structure: PubmedArticle -> MedlineCitation -> Article -> ELocationID
        article = root.find(".//Article")
        if article is None:
            return

        # Use .//ELocationID to match original behavior (recursively find in Article)
        for eloc in article.findall(".//ELocationID"):
            eid_type = eloc.get("EIdType")
            if eid_type in ("doi", "pii") and ids[eid_type] is None:
                if text := cls._normalize_text(eloc.text):
                    ids[eid_type] = text

    @classmethod
    def _process_article_id_list(
        cls, root: Element, ids: dict[str, str | None]
    ) -> None:
        """Process ArticleIdList elements to populate identifiers.

        Modifies the ids dictionary in-place.
        """
        # XML structure: PubmedArticle -> PubmedData -> ArticleIdList
        # Use .//ArticleIdList to match original behavior
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is None:
            return

        type_map = {
            "doi": "doi",
            "pii": "pii",
            "pmc": "pmc_id",
            "mid": "mid",
            "publisher-id": "publisher_id",
        }

        for aid in article_id_list.findall("ArticleId"):
            id_type = aid.get("IdType")
            if not id_type or id_type not in type_map:
                continue

            field_name = type_map[id_type]
            if ids[field_name] is not None:
                continue

            if text := cls._normalize_text(aid.text):
                ids[field_name] = text

