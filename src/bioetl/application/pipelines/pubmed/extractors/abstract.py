"""Abstract extraction from PubMed XML elements.

Handles structured and unstructured abstract parsing.
"""

from __future__ import annotations

from typing import cast
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor


class AbstractExtractor(BaseFieldExtractor):
    """Extractor for abstract content from PubMed XML.

    Handles:
    - Simple abstracts with single AbstractText
    - Structured abstracts with labeled sections
    - Inline elements within abstract text
    """

    def extract(self, element: Element | None) -> list[str] | None:
        """Извлечь сырые данные из XML элемента Abstract.

        Args:
            element: The Article element.

        Returns:
            List of text parts with labels, or None if no abstract.
        """
        if element is None:
            return None

        abstract_node = element.find(".//Abstract")
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

        return texts if texts else None

    def normalize(self, raw_value: list[str]) -> str:
        """Нормализовать извлечённый текст абстракта.

        Args:
            raw_value: List of abstract text parts.

        Returns:
            Combined abstract text.
        """
        return " ".join(raw_value)

    @classmethod
    def extract_abstract(cls, article_node: Element | None) -> str | None:
        """Extract abstract, handling structured abstracts with multiple sections.

        Args:
            article_node: The Article element.

        Returns:
            Combined abstract text or None.
        """
        return cast("str | None", cls().process(article_node))
