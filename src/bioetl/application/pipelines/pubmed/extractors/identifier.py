"""Identifier extraction from PubMed XML elements.

Handles extraction of DOI, PMC ID, and other article identifiers.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


class IdentifierExtractor:
    """Extractor for article identifiers from PubMed XML.

    Handles:
    - DOI from ELocationID or ArticleIdList
    - PMC ID from ArticleIdList
    - PMID (via get_text utility)
    """

    @classmethod
    def extract_doi(cls, root: ET.Element) -> str | None:
        """Extract DOI from ArticleIdList or ELocationID.

        First tries ELocationID with EIdType="doi", then falls back
        to ArticleIdList with IdType="doi".

        Args:
            root: Root PubmedArticle element.

        Returns:
            DOI string or None.

        """
        article = root.find(".//Article")
        if article is None:
            return None

        # Try ELocationID first
        for eloc in article.findall(".//ELocationID"):
            if eloc.get("EIdType") == "doi" and eloc.text:
                return eloc.text.strip()

        # Fallback to ArticleIdList
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "doi" and aid.text:
                    return aid.text.strip()

        return None

    @classmethod
    def extract_pmc_id(cls, root: ET.Element) -> str | None:
        """Extract PubMed Central ID from ArticleIdList.

        Args:
            root: Root PubmedArticle element.

        Returns:
            PMC ID string or None.

        """
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "pmc" and aid.text:
                    return aid.text.strip()
        return None
