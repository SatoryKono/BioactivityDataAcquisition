"""Helper for identifier extraction strategies.

Extracts complex identifier logic from IdentifierExtractor to reduce class size
and complexity.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

if TYPE_CHECKING:
    from bioetl.application.pipelines.pubmed.extractors.identifier_types import (
        CombinedIdentifiers,
    )


class IdentifierExtractionHelper:
    """Helper class for extracting identifiers from PubMed XML."""

    @staticmethod
    def extract_from_article(
        root: Element,
        result: CombinedIdentifiers,
        normalize_func: Callable[[str | None], str | None],
    ) -> None:
        """Extract identifiers from Article/ELocationID elements.

        Modifies result dictionary in-place.
        """
        article = root.find(".//Article")
        if article is None:
            return

        for eloc in article.findall(".//ELocationID"):
            eid_type = eloc.get("EIdType")
            if not eid_type or not eloc.text:
                continue

            normalized = normalize_func(eloc.text)
            if not normalized:
                continue

            if eid_type == "doi":
                result["doi"] = normalized
            elif eid_type == "pii":
                result["pii"] = normalized

    @staticmethod
    def extract_from_article_id_list(
        root: Element,
        result: CombinedIdentifiers,
        normalize_func: Callable[[str | None], str | None],
    ) -> None:
        """Extract identifiers from ArticleIdList elements.

        Modifies result dictionary in-place.
        """
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is None:
            return

        id_map: dict[str, str] = {
            "doi": "doi",
            "pii": "pii",
            "pmc": "pmc_id",
            "mid": "mid",
            "publisher-id": "publisher_id",
        }

        for aid in article_id_list.findall("ArticleId"):
            id_type = aid.get("IdType")
            if not id_type or not aid.text:
                continue

            target_field = id_map.get(id_type)
            if not target_field:
                continue

            # Skip if already set (priority logic)
            # Only DOI and PII have priority rules (ELocationID > ArticleIdList),
            # but others are simple first-match or overwrite?
            # Existing logic was:
            # if id_type == "doi" and result["doi"] is None: ...
            # if id_type == "pii" and result["pii"] is None: ...
            # else: overwrite or set
            #
            # But dict iteration order is not guaranteed in older python, though XML order is.
            # Assuming first match in XML is preferred for single-value fields if not "doi"/"pii".
            # For "doi"/"pii", we only set if None (because ELocationID might have set it).

            if target_field in ("doi", "pii") and result[target_field] is not None:  # type: ignore[literal-required]
                continue

            normalized = normalize_func(aid.text)
            if normalized:
                result[target_field] = normalized  # type: ignore[literal-required]

    @staticmethod
    def extract_doi_raw(root: Element) -> str | None:
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

    @staticmethod
    def extract_pmc_raw(root: Element) -> str | None:
        """Extract raw PMC ID from ArticleIdList."""
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "pmc" and aid.text:
                    return aid.text
        return None

    @staticmethod
    def extract_pii_raw(root: Element) -> str | None:
        """Extract Publisher Item Identifier (PII).

        Tries ELocationID first, then ArticleIdList.
        """
        # Try ELocationID first
        article = root.find(".//Article")
        if article is not None:
            for eloc in article.findall(".//ELocationID"):
                if eloc.get("EIdType") == "pii" and eloc.text:
                    return eloc.text

        # Fallback to ArticleIdList
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "pii" and aid.text:
                    return aid.text

        return None

    @staticmethod
    def extract_mid_raw(root: Element) -> str | None:
        """Extract Manuscript ID (MID) used in PMC submission."""
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "mid" and aid.text:
                    return aid.text
        return None

    @staticmethod
    def extract_publisher_id_raw(root: Element) -> str | None:
        """Extract publisher-specific identifier."""
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "publisher-id" and aid.text:
                    return aid.text
        return None
