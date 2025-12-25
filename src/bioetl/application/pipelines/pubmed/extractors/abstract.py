"""Abstract extraction from PubMed XML elements.

Handles structured and unstructured abstract parsing.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


class AbstractExtractor:
    """Extractor for abstract content from PubMed XML.

    Handles:
    - Simple abstracts with single AbstractText
    - Structured abstracts with labeled sections
    - Inline elements within abstract text
    """

    @classmethod
    def extract_abstract(cls, article_node: ET.Element | None) -> str | None:
        """Extract abstract, handling structured abstracts with multiple sections.

        Args:
            article_node: The Article element.

        Returns:
            Combined abstract text or None.

        """
        if article_node is None:
            return None

        abstract_node = article_node.find(".//Abstract")
        if abstract_node is None:
            return None

        # Collect all AbstractText sections
        texts = []
        for abstract_text in abstract_node.findall("AbstractText"):
            label = abstract_text.get("Label")

            # Handle inline elements
            full_text = "".join(abstract_text.itertext())

            if label and full_text.strip():
                texts.append(f"{label}: {full_text.strip()}")
            elif full_text.strip():
                texts.append(full_text.strip())

        return " ".join(texts) if texts else None
