"""Common XML utilities for PubMed extractors.

Provides reusable low-level functions for extracting data from XML elements.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


def get_text(node: ET.Element | None) -> str | None:
    """Extract text from an XML node, returning None if node is None or empty."""
    if node is not None and node.text:
        return node.text.strip()
    return None


def get_int(node: ET.Element | None) -> int | None:
    """Extract integer from a node, returning None if invalid."""
    if node is not None and node.text:
        text = node.text.strip()
        if text:
            try:
                return int(text)
            except ValueError:
                pass
    return None
