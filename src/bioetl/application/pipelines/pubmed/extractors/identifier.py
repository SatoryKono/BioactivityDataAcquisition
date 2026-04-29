"""Identifier extraction from PubMed XML elements."""

from __future__ import annotations

from typing import cast
from xml.etree.ElementTree import Element  # nosec B405

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


_ARTICLE_ID_KEY_MAP: dict[str, str] = {
    "pubmed": "pubmed",
    "doi": "doi",
    "pmc": "pmc",
    "pii": "pii",
    "mid": "mid",
    "publisher-id": "publisher_id",
    "pmcid": "pmcid",
    "medline": "medline",
}


def _assign_known_article_id(
    result: AllArticleIds,
    *,
    id_type: str,
    value: str,
) -> bool:
    """Assign a mapped ArticleId and return whether assignment was handled."""
    key = _ARTICLE_ID_KEY_MAP.get(id_type)
    if key is None:
        return False
    result[key] = value  # type: ignore[literal-required]
    return True


class IdentifierExtractor(BaseFieldExtractor):
    """Extractor for article identifiers from PubMed XML."""

    def extract(self, element: Element | None) -> RawIdentifiers | None:
        """Extract raw doi/pmc_id from XML.

        Args:
            element: Root ``PubmedArticle`` element to extract identifiers from.
                Returns None immediately when None.

        Returns:
            RawIdentifiers dict with ``doi`` and ``pmc_id`` fields, or None when
            the element is absent.
        """
        if element is None:
            return None

        # Use the optimized single-pass extractor
        all_ids = self.extract_all_identifiers(element)
        return RawIdentifiers(
            doi=all_ids["doi"],
            pmc_id=all_ids["pmc_id"],
        )

    def normalize(self, raw_value: object) -> NormalizedIdentifiers:
        """Normalize extracted identifiers.

        Args:
            raw_value: Raw identifier dict (``RawIdentifiers``) from the ``extract`` step.

        Returns:
            NormalizedIdentifiers with whitespace-stripped ``doi`` and ``pmc_id`` values.
        """
        raw_identifiers = cast("RawIdentifiers", raw_value)
        return NormalizedIdentifiers(
            doi=self._normalize_text(raw_identifiers.get("doi")),
            pmc_id=self._normalize_text(raw_identifiers.get("pmc_id")),
        )

    def _normalize_text(self, text: str | None) -> str | None:
        """Normalize text by stripping whitespace."""
        return text.strip() if text else None

    @classmethod
    def extract_doi(cls, root: Element) -> str | None:
        """Extract DOI from ArticleIdList or ELocationID.

        Args:
            root: Root PubmedArticle XML element.

        Returns:
            DOI string with whitespace stripped, or None if not present.
        """
        return cls.extract_all_identifiers(root)["doi"]

    @classmethod
    def extract_pmc_id(cls, root: Element) -> str | None:
        """Extract PMC ID from ArticleIdList.

        Args:
            root: Root PubmedArticle XML element.

        Returns:
            PubMed Central identifier string with whitespace stripped, or None if absent.
        """
        return cls.extract_all_identifiers(root)["pmc_id"]

    @classmethod
    def extract_all_identifiers(cls, root: Element) -> dict[str, str | None]:
        """Extract doi/pii/pmc_id/mid/publisher_id in a single pass.

        Args:
            root: Root PubmedArticle XML element scanned for ELocationID and ArticleIdList.

        Returns:
            Dictionary with keys ``doi``, ``pii``, ``pmc_id``, ``mid``, ``publisher_id``,
            each mapped to the normalized string value or None when absent.
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
        """Scan ELocationID elements for identifiers."""
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
        """Extract all identifiers from ArticleIdList, preserving unknown keys.

        Args:
            root: Root PubmedArticle XML element containing the ArticleIdList section.

        Returns:
            AllArticleIds TypedDict with known identifier keys (``pubmed``, ``doi``,
            ``pmc``, ``pii``, ``mid``, ``publisher_id``, ``pmcid``, ``medline``) and
            an ``other_ids`` dict for unrecognized IdType values.
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

        for aid in article_id_list.findall("ArticleId"):
            id_type = aid.get("IdType")
            if not id_type or not aid.text:
                continue

            normalized_value = extractor._normalize_text(aid.text)
            if not normalized_value:
                continue

            if not _assign_known_article_id(
                result,
                id_type=id_type,
                value=normalized_value,
            ):
                result["other_ids"][id_type] = normalized_value

        return result

    @classmethod
    def extract_elocation_ids(cls, root: Element) -> ELocationIds:
        """Extract doi/pii from ELocationID elements.

        Args:
            root: Root PubmedArticle XML element scanned for ELocationID children.

        Returns:
            ELocationIds TypedDict with ``doi`` and ``pii`` fields, each None when absent.
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
            root: Root PubmedArticle XML element.

        Returns:
            PII string with whitespace stripped, or None if not present.
        """
        return cls.extract_all_identifiers(root)["pii"]

    @classmethod
    def extract_mid(cls, root: Element) -> str | None:
        """Extract Manuscript ID (MID).

        Args:
            root: Root PubmedArticle XML element.

        Returns:
            Manuscript ID string with whitespace stripped, or None if not present.
        """
        return cls.extract_all_identifiers(root)["mid"]

    @classmethod
    def extract_publisher_id(cls, root: Element) -> str | None:
        """Extract publisher-specific identifier.

        Args:
            root: Root PubmedArticle XML element.

        Returns:
            Publisher-assigned identifier string with whitespace stripped, or None if absent.
        """
        return cls.extract_all_identifiers(root)["publisher_id"]
