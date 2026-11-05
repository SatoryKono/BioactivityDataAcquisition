# mypy: disable-error-code="import-untyped"
# Host attrs/methods provided by concrete composition.
"""PubMed XML processing utilities.

Provides XML parsing and record extraction for PubMed API responses.
Extracted from the PubMed adapter module for better separation of concerns.
"""

from __future__ import annotations

import time
import typing
import xml.etree as etree

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import DefusedXMLParser, ParseError

from bioetl.domain.types import JsonDict

__all__ = ["PubMedXmlProcessor"]

_MAX_XML_BYTES = 31457280

if typing.TYPE_CHECKING:

    class XmlElementProtocol(typing.Protocol):
        text: str | None

        def find(self, path: str) -> XmlElementProtocol | None: ...

        def findall(self, path: str) -> list[XmlElementProtocol]: ...

    Element = XmlElementProtocol
else:
    Element = object


class LimitedParseTarget(etree.ElementTree.TreeBuilder):
    """DefusedXML parse target with element-count and wall-time limits."""

    def __init__(
        self,
        *args: typing.Any,  # Any: TreeBuilder ctor passthrough
        **kwargs: typing.Any,  # Any: TreeBuilder ctor passthrough
    ) -> None:
        super().__init__(*args, **kwargs)
        self.element_count = 0
        self.max_elements = 100000
        self.start_time = time.monotonic()
        self.max_time = 5.0

    def _raise_if_time_exceeded(self) -> None:
        if time.monotonic() - self.start_time > self.max_time:
            raise ValueError("XML time limit exceeded")

    def start(
        self,
        tag: str,
        attrs: dict[str, str],
    ) -> typing.Any:  # Any: TreeBuilder.start returns element nodes
        self.element_count += 1
        if self.element_count > self.max_elements:
            raise ValueError("XML element limit exceeded")
        self._raise_if_time_exceeded()
        return super().start(tag, attrs)

    def data(self, data: str) -> None:
        self._raise_if_time_exceeded()
        super().data(data)

    def end(self, tag: str) -> typing.Any:  # Any: TreeBuilder.end returns element nodes
        self._raise_if_time_exceeded()
        return super().end(tag)


class PubMedXmlProcessor:
    """Processes PubMed XML responses and extracts article records."""

    @staticmethod
    def parse_response(xml_text: str) -> Element | None:
        """Parse XML response text into ElementTree.

        Args:
            xml_text: Raw XML response text

        Returns:
            Parsed XML root element, or None if parsing fails due to
            malformed/hostile XML (ParseError / DefusedXmlException).

        Raises:
            ValueError: When size, element-count, or wall-time resource
                limits are exceeded. Callers must treat this as a hard
                failure rather than an empty batch.
        """
        # Char-count fast reject; UTF-8 bytes are always >= Unicode length.
        if len(xml_text) > _MAX_XML_BYTES:
            raise ValueError("XML size limit exceeded")
        # Bounded encode: at most `_MAX_XML_BYTES` characters.
        if len(xml_text.encode("utf-8")) > _MAX_XML_BYTES:
            raise ValueError("XML size limit exceeded")

        try:
            target = LimitedParseTarget()
            parser = DefusedXMLParser(
                target=target,
                forbid_dtd=False,
                forbid_entities=True,
                forbid_external=True,
            )
            parser.feed(xml_text)
            parsed_root = parser.close()
            if time.monotonic() - target.start_time > target.max_time:
                raise ValueError("XML time limit exceeded")
            return typing.cast("Element", parsed_root)
        except (ParseError, DefusedXmlException):
            # Malformed/hostile XML → empty parse; resource limits raise ValueError.
            return None

    @staticmethod
    def extract_record(
        article_node: Element,
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
            "_raw_xml": SafeET.tostring(
                typing.cast(
                    typing.Any,  # Any: SafeET.tostring expects etree Element
                    article_node,
                ),
                encoding="unicode",
            ),
        }

    @staticmethod
    def find_articles(root: Element) -> list[Element]:
        """Find all PubmedArticle elements in the XML tree.

        Args:
            root: XML root element

        Returns:
            List of PubmedArticle elements
        """
        return root.findall(".//PubmedArticle")

    @staticmethod
    def extract_all_records(
        root: Element,
    ) -> list[JsonDict]:  # Any: untyped API JSON record
        """Extract all article records from XML root.

        Args:
            root: XML root element

        Returns:
            List of article record dictionaries
        """
        records: list[JsonDict] = []
        for article_node in PubMedXmlProcessor.find_articles(root):
            records.append(PubMedXmlProcessor.extract_record(article_node))
        return records
