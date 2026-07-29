# mypy: disable-error-code="import-untyped"
# Host attrs/methods provided by concrete composition.
"""PubMed XML processing utilities.

Provides XML parsing and record extraction for PubMed API responses.
Extracted from the PubMed adapter module for better separation of concerns.
"""

from __future__ import annotations

from typing import Any, cast

__all__ = ["PubMedXmlProcessor"]


import xml.etree.ElementTree as ET  # nosec B405

import defusedxml.ElementTree as defused_ET

from bioetl.domain.types import JsonDict


class PubMedXmlProcessor:
    """Processes PubMed XML responses and extracts article records."""

    @staticmethod
    def parse_response(xml_text: str) -> ET.Element | None:
        """Parse XML response text into ElementTree.

        Args:
            xml_text: Raw XML response text

        Returns:
            Parsed XML root element, or None if parsing fails
        """
        try:
            parsed_root: ET.Element = defused_ET.fromstring(xml_text)
            return parsed_root
        except (ET.ParseError, cast(type[BaseException], getattr(defused_ET, "EntitiesForbidden", Exception))):
            return None

    @staticmethod
    def extract_record(
        article_node: ET.Element,
    ) -> JsonDict:  # Any: untyped API JSON record
        """Extract record dict from a PubmedArticle XML node.

        Args:
            article_node: XML element representing a PubMed article

        Returns:
            Dictionary with pmid, article_title, and _raw_xml fields
        """
        pmid_node = article_node.find(".//PMID")
        title_node = article_node.find(".//ArticleTitle")
        return {
            "pmid": pmid_node.text if pmid_node is not None else None,
            "article_title": (
                title_node.text if title_node is not None else "No title found"
            ),
            "_raw_xml": ET.tostring(article_node, encoding="unicode"),
        }

    @staticmethod
    def find_articles(root: ET.Element) -> list[ET.Element]:
        """Find all PubmedArticle elements in the XML tree.

        Args:
            root: XML root element

        Returns:
            List of PubmedArticle elements
        """
        return root.findall(".//PubmedArticle")

    @staticmethod
    def extract_all_records(
        root: ET.Element,
    ) -> list[JsonDict]:  # Any: untyped API JSON record
        """Extract all article records from XML root.

        Args:
            root: XML root element

        Returns:
            List of article record dictionaries
        """
        records = []
        for article_node in PubMedXmlProcessor.find_articles(root):
            records.append(PubMedXmlProcessor.extract_record(article_node))
        return records
