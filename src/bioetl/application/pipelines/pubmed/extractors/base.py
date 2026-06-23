"""Base class for PubMed XML field extractors.

Implements Template Method pattern for consistent extraction process.
"""

from __future__ import annotations

__all__ = ["BaseFieldExtractor"]


from abc import ABC, abstractmethod
from xml.etree.ElementTree import Element  # nosec B405


class BaseFieldExtractor(ABC):
    """Template Method for extracting fields from PubMed XML.

    Subclasses implement extract() and normalize() for specific fields.
    The process() method combines them into a single processing workflow.

    Example:
        >>> class MyExtractor(BaseFieldExtractor):
        ...     def extract(self, element):
        ...         return element.find("MyField").text
        ...     def normalize(self, raw_value):
        ...         return raw_value.strip().upper()
        >>> extractor = MyExtractor()
        >>> result = extractor.process(some_element)
    """

    @abstractmethod
    def extract(
        self, element: Element | None
    ) -> object:  # object: XML-derived values (str, list, dict, None)
        """Extract raw data from an XML element.

        Args:
            element: XML element to extract data from.

        Returns:
            Raw data (may be None, a string, a list, etc.).
        """
        ...

    @abstractmethod
    def normalize(self, raw_value: object) -> object:  # object: XML-derived values
        """Normalize an extracted value.

        Args:
            raw_value: Raw value from extract().

        Returns:
            Normalized value.
        """
        ...

    def process(self, element: Element | None) -> object:  # object: XML-derived values
        """Template method: extract → normalize.

        Performs the full extraction and normalization cycle.

        Args:
            element: XML element to process.

        Returns:
            Normalized value, or None.
        """
        raw = self.extract(element)
        return self.normalize(raw) if raw is not None else None
