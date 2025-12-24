"""XML parsing utilities for PubMed records.

Provides reusable functions for extracting data from PubMed XML.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import ClassVar


class PubMedXMLParser:
    """Helper class for parsing PubMed XML elements.

    Provides methods for extracting text, integers, dates, and lists
    from PubMed XML structure.
    """

    # Month name to number mapping
    MONTH_MAP: ClassVar[dict[str, str]] = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }

    @staticmethod
    def get_text(node: ET.Element | None) -> str | None:
        """Extract text from an XML node, returning None if node is None or empty."""
        if node is not None and node.text:
            return node.text.strip()
        return None

    @staticmethod
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

    @classmethod
    def format_date(
        cls,
        year: str | None,
        month: str | None,
        day: str | None,
    ) -> str | None:
        """Format date components into ISO date string (YYYY-MM-DD or partial)."""
        if not year:
            return None

        parts = [year]
        if month:
            month_lower = month.lower()[:3]
            month_num = cls.MONTH_MAP.get(month_lower, month.zfill(2))
            parts.append(month_num)

            if day:
                parts.append(day.zfill(2))

        return "-".join(parts)

    @classmethod
    def extract_date(
        cls,
        date_node: ET.Element | None,
    ) -> tuple[str | None, int | None]:
        """Extract date string and year from a date element.

        Returns:
            Tuple of (formatted_date_string, year_int)
        """
        if date_node is None:
            return None, None

        year = cls.get_text(date_node.find("Year"))
        month = cls.get_text(date_node.find("Month"))
        day = cls.get_text(date_node.find("Day"))

        date_str = cls.format_date(year, month, day)
        year_int = cls.get_int(date_node.find("Year"))

        return date_str, year_int

    @classmethod
    def extract_history_date(
        cls,
        history_node: ET.Element | None,
        pub_status: str,
    ) -> str | None:
        """Extract a specific date from PubMedPubDate history.

        Args:
            history_node: The History element from PubmedData.
            pub_status: PubStatus value to look for (received, revised, accepted, etc.)

        Returns:
            ISO formatted date string or None.
        """
        if history_node is None:
            return None

        for date_node in history_node.findall("PubMedPubDate"):
            if date_node.get("PubStatus") == pub_status:
                date_str, _ = cls.extract_date(date_node)
                return date_str
        return None

    @classmethod
    def extract_article_date(
        cls,
        article_node: ET.Element | None,
        date_type: str,
    ) -> str | None:
        """Extract date from ArticleDate element by DateType attribute.

        Args:
            article_node: The Article element.
            date_type: DateType attribute value (e.g., "Electronic").

        Returns:
            ISO formatted date string or None.
        """
        if article_node is None:
            return None

        for date_node in article_node.findall(".//ArticleDate"):
            if date_node.get("DateType") == date_type:
                date_str, _ = cls.extract_date(date_node)
                return date_str
        return None

    @classmethod
    def parse_authors(cls, article_node: ET.Element) -> list[str]:
        """Extract list of authors in 'LastName, Initials' format."""
        author_list = article_node.find(".//AuthorList")
        if author_list is None:
            return []

        authors = []
        for author in author_list.findall("Author"):
            last_name = cls.get_text(author.find("LastName"))
            initials = cls.get_text(author.find("Initials"))
            fore_name = cls.get_text(author.find("ForeName"))

            if last_name:
                if initials:
                    authors.append(f"{last_name}, {initials}")
                elif fore_name:
                    authors.append(f"{last_name}, {fore_name}")
                else:
                    authors.append(last_name)
            else:
                # Collective/group author
                collective = cls.get_text(author.find("CollectiveName"))
                if collective:
                    authors.append(collective)

        return authors

    @classmethod
    def parse_publication_types(cls, article_node: ET.Element) -> list[str]:
        """Extract publication types."""
        pub_types = []
        type_list = article_node.find(".//PublicationTypeList")
        if type_list is not None:
            for pub_type in type_list.findall("PublicationType"):
                if pub_type.text:
                    pub_types.append(pub_type.text.strip())
        return pub_types

    @classmethod
    def parse_keywords(cls, medline_citation: ET.Element | None) -> list[str]:
        """Extract keywords from KeywordList."""
        if medline_citation is None:
            return []

        keywords = []
        keyword_list = medline_citation.find(".//KeywordList")
        if keyword_list is not None:
            for kw in keyword_list.findall("Keyword"):
                if kw.text:
                    keywords.append(kw.text.strip())
        return keywords

    @classmethod
    def parse_mesh_terms(cls, medline_citation: ET.Element | None) -> list[str]:
        """Extract MeSH terms from MeshHeadingList."""
        if medline_citation is None:
            return []

        mesh_terms = []
        mesh_list = medline_citation.find(".//MeshHeadingList")
        if mesh_list is not None:
            for heading in mesh_list.findall("MeshHeading"):
                descriptor = heading.find("DescriptorName")
                if descriptor is not None and descriptor.text:
                    mesh_terms.append(descriptor.text.strip())
        return mesh_terms

    @classmethod
    def extract_doi(cls, root: ET.Element) -> str | None:
        """Extract DOI from ArticleIdList or ELocationID."""
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
        """Extract PubMed Central ID."""
        article_id_list = root.find(".//ArticleIdList")
        if article_id_list is not None:
            for aid in article_id_list.findall("ArticleId"):
                if aid.get("IdType") == "pmc" and aid.text:
                    return aid.text.strip()
        return None

    @classmethod
    def extract_abstract(cls, article_node: ET.Element | None) -> str | None:
        """Extract abstract, handling structured abstracts with multiple sections."""
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
