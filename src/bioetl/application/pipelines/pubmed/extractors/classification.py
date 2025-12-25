"""Classification extraction from PubMed XML elements.

Handles extraction of keywords, MeSH terms, and publication types.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


class ClassificationExtractor:
    """Extractor for classification data from PubMed XML.

    Handles:
    - Keywords from KeywordList
    - MeSH terms from MeshHeadingList
    - Publication types from PublicationTypeList
    """

    @classmethod
    def parse_keywords(cls, medline_citation: ET.Element | None) -> list[str]:
        """Extract keywords from KeywordList.

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of keyword strings.

        """
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
        """Extract MeSH terms from MeshHeadingList.

        Args:
            medline_citation: The MedlineCitation element.

        Returns:
            List of MeSH descriptor names.

        """
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
    def parse_publication_types(cls, article_node: ET.Element) -> list[str]:
        """Extract publication types from PublicationTypeList.

        Args:
            article_node: The Article element.

        Returns:
            List of publication type strings.

        """
        pub_types = []
        type_list = article_node.find(".//PublicationTypeList")
        if type_list is not None:
            for pub_type in type_list.findall("PublicationType"):
                if pub_type.text:
                    pub_types.append(pub_type.text.strip())
        return pub_types
