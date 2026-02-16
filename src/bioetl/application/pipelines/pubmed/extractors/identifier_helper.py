"""Helper for identifier extraction strategies.

Extracts complex identifier logic from IdentifierExtractor to reduce class size
and complexity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

if TYPE_CHECKING:
    from bioetl.application.pipelines.pubmed.extractors.identifier import (
        CombinedIdentifiers,
    )


class IdentifierExtractionHelper:
    """Helper class for extracting identifiers from PubMed XML."""

    @staticmethod
    def extract_from_article(
        root: Element,
        result: CombinedIdentifiers,
        normalize_func: callable,
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
        normalize_func: callable,
    ) -> None:
        """Extract identifiers from ArticleIdList elements.

        Modifies result dictionary in-place.
        """
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is None:
            return

        for aid in article_id_list.findall("ArticleId"):
            id_type = aid.get("IdType")
            if not id_type or not aid.text:
                continue

            normalized = normalize_func(aid.text)
            if not normalized:
                continue

            if id_type == "doi" and result["doi"] is None:
                result["doi"] = normalized
            elif id_type == "pii" and result["pii"] is None:
                result["pii"] = normalized
            elif id_type == "pmc":
                result["pmc_id"] = normalized
            elif id_type == "mid":
                result["mid"] = normalized
            elif id_type == "publisher-id":
                result["publisher_id"] = normalized
