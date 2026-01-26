"""Author extraction from PubMed XML elements.

Handles parsing of author lists including individual and collective authors.
"""

from __future__ import annotations

from typing import TypedDict
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor
from bioetl.application.pipelines.pubmed.xml_utils import get_text


class RawAuthor(TypedDict, total=False):
    """Raw author data before normalization."""

    last_name: str | None
    initials: str | None
    fore_name: str | None
    collective_name: str | None
    affiliations: list[str] | None


class AuthorExtractor(BaseFieldExtractor):
    """Extractor for author information from PubMed XML.

    Handles:
    - Individual authors with LastName, Initials/ForeName
    - Collective/group authors
    - Author affiliations (AffiliationInfo)
    - Empty author lists
    """

    def extract(self, element: Element | None) -> list[RawAuthor] | None:
        """Извлечь сырые данные об авторах из XML.

        Args:
            element: The Article element containing AuthorList.

        Returns:
            List of raw author dicts, or None if no authors.
        """
        if element is None:
            return None

        author_list = element.find(".//AuthorList")
        if author_list is None:
            return None

        raw_authors: list[RawAuthor] = []
        for author in author_list.findall("Author"):
            # Extract affiliations
            affiliations = []
            for info in author.findall("AffiliationInfo"):
                aff_text = get_text(info.find("Affiliation"))
                if aff_text:
                    affiliations.append(aff_text)

            raw_authors.append(
                RawAuthor(
                    last_name=get_text(author.find("LastName")),
                    initials=get_text(author.find("Initials")),
                    fore_name=get_text(author.find("ForeName")),
                    collective_name=get_text(author.find("CollectiveName")),
                    affiliations=affiliations if affiliations else None,
                )
            )

        return raw_authors if raw_authors else None

    def normalize(self, raw_value: list[RawAuthor]) -> list[str]:
        """Нормализовать список авторов в формат 'LastName, Initials'.

        Args:
            raw_value: List of raw author dicts.

        Returns:
            List of formatted author names.
        """
        authors = []
        for raw in raw_value:
            last_name = raw.get("last_name")
            initials = raw.get("initials")
            fore_name = raw.get("fore_name")
            collective = raw.get("collective_name")

            if last_name:
                if initials:
                    authors.append(f"{last_name}, {initials}")
                elif fore_name:
                    authors.append(f"{last_name}, {fore_name}")
                else:
                    authors.append(last_name)
            elif collective:
                authors.append(collective)

        return authors

    def process(self, element: Element | None) -> list[str]:
        """Template method: extract → normalize.

        Args:
            element: XML элемент для обработки.

        Returns:
            List of formatted author names (empty list if no authors).
        """
        raw = self.extract(element)
        return self.normalize(raw) if raw is not None else []

    @classmethod
    def parse_authors(cls, article_node: Element) -> list[str]:
        """Extract list of authors in 'LastName, Initials' format.

        Args:
            article_node: The Article element containing AuthorList.

        Returns:
            List of formatted author names.
        """
        return cls().process(article_node)

    @classmethod
    def parse_affiliations(cls, article_node: Element) -> list[str]:
        """Extract unique list of affiliations from all authors.

        Args:
            article_node: The Article element containing AuthorList.

        Returns:
            List of unique affiliation strings.
        """
        extractor = cls()
        raw_authors = extractor.extract(article_node)
        if not raw_authors:
            return []

        # Collect all affiliations from all authors
        all_affiliations: set[str] = set()
        for author in raw_authors:
            affs = author.get("affiliations")
            if affs:
                all_affiliations.update(affs)

        return sorted(list(all_affiliations))
