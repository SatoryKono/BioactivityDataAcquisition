"""PubMed XML processing utilities.

Provides XML parsing and record extraction for PubMed API responses.
Extracted from pubmed_client.py for better separation of concerns.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


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
            return ET.fromstring(xml_text)
        except ET.ParseError:
            return None

    @staticmethod
    def extract_record(article_node: ET.Element) -> dict[str, Any]:
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
    def extract_all_records(root: ET.Element) -> list[dict[str, Any]]:
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
