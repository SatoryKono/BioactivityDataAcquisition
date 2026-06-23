"""Common XML utilities for PubMed extractors.

Provides reusable low-level functions for extracting data from XML elements.
"""

from __future__ import annotations

__all__ = ["get_int", "get_text"]


import xml.etree.ElementTree as ET  # nosec B405


def get_text(node: ET.Element | None) -> str | None:
    """Extract text content from an XML element.

    Safely extracts and strips whitespace from XML element text content.
    Handles None elements and empty text gracefully.

    Args:
        node: XML element to extract text from, or None.

    Returns:
        Stripped text content if element exists and has non-empty text,
        None otherwise.

    Example:
        >>> import defusedxml.ElementTree as ET
        >>> elem = ET.fromstring("<title>  PubMed Article  </title>")
        >>> get_text(elem)
        'PubMed Article'
        >>> get_text(None)
        None
        >>> empty = ET.fromstring("<title></title>")
        >>> get_text(empty)
        None

    """
    if node is not None and node.text:
        return node.text.strip()
    return None


def get_int(node: ET.Element | None) -> int | None:
    """Extract integer value from an XML element.

    Safely parses integer from XML element text content.
    Returns None for missing elements, empty text, or non-integer values.

    Args:
        node: XML element containing integer text, or None.

    Returns:
        Parsed integer if element exists and contains valid integer text,
        None otherwise (including for non-numeric text).

    Example:
        >>> import defusedxml.ElementTree as ET
        >>> year = ET.fromstring("<Year>2024</Year>")
        >>> get_int(year)
        2024
        >>> get_int(None)
        None
        >>> invalid = ET.fromstring("<Year>invalid</Year>")
        >>> get_int(invalid)
        None
        >>> empty = ET.fromstring("<Year>  </Year>")
        >>> get_int(empty)
        None

    """
    if node is not None and node.text:
        text = node.text.strip()
        if text:
            try:
                return int(text)
            except ValueError:
                pass  # Why: XML date text not parseable as integer; return None as fallback
    return None
