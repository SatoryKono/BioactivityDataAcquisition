"""Author extraction from PubMed XML elements.

Handles parsing of author lists including individual and collective authors.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.xml_utils import get_text


class AuthorExtractor:
    """Extractor for author information from PubMed XML.

    Handles:
    - Individual authors with LastName, Initials/ForeName
    - Collective/group authors
    - Empty author lists
    """

    @classmethod
    def parse_authors(cls, article_node: ET.Element) -> list[str]:
        """Extract list of authors in 'LastName, Initials' format.

        Args:
            article_node: The Article element containing AuthorList.

        Returns:
            List of formatted author names.

        """
        author_list = article_node.find(".//AuthorList")
        if author_list is None:
            return []

        authors = []
        for author in author_list.findall("Author"):
            last_name = get_text(author.find("LastName"))
            initials = get_text(author.find("Initials"))
            fore_name = get_text(author.find("ForeName"))

            if last_name:
                if initials:
                    authors.append(f"{last_name}, {initials}")
                elif fore_name:
                    authors.append(f"{last_name}, {fore_name}")
                else:
                    authors.append(last_name)
            else:
                # Collective/group author
                collective = get_text(author.find("CollectiveName"))
                if collective:
                    authors.append(collective)

        return authors
