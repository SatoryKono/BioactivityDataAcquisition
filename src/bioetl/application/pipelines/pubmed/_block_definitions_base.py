"""Base classes for PubMed block implementations."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class _PubMedXmlBlock:
    """Base helper for PubMed extraction blocks over cached XML roots."""

    def __init__(
        self,
        root_resolver: Callable[[], ET.Element | None],
    ) -> None:
        self._root_resolver = root_resolver

    def _resolve_root(self) -> ET.Element | None:
        return self._root_resolver()

    def _resolve_article_context(
        self,
    ) -> tuple[ET.Element | None, ET.Element | None, ET.Element | None]:
        root = self._resolve_root()
        if root is None:
            return None, None, None
        return (
            root.find(".//Article"),
            root.find(".//MedlineCitation"),
            root.find(".//PubmedData"),
        )


__all__ = ["_PubMedXmlBlock"]
