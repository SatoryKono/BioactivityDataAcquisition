"""Author extraction from PubMed XML elements.

Handles parsing of author lists including individual and collective authors.
Supports structured affiliation extraction with institutional identifiers.

PII Safety (RULES.md §5.4):
    Author names and email addresses extracted here are PII fields.
    Salted SHA-256 hashing is applied at the transformer level
    (PubMedPublicationTransformer) before any data reaches the Silver layer:
    - Author names → hash_pii_list() → hashed before Silver storage
    - Email addresses → PiiHasherPort.hash_value() → stored as email_hash
    Raw PII values MUST NOT persist beyond the Bronze→Silver transformation.
"""

from __future__ import annotations

__all__ = ["EMAIL_PATTERN", "AuthorExtractor", "RawAuthor", "StructuredAffiliation"]


import re
from typing import TypedDict, cast
from xml.etree.ElementTree import Element

from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor
from bioetl.application.pipelines.pubmed.xml_parser import get_text

# Email pattern for detection and extraction
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


class StructuredAffiliation(TypedDict, total=False):
    """Structured affiliation with identifier metadata.

    MEDLINE AffiliationInfo can contain Identifier elements linking to
    institutional databases like ROR (Research Organization Registry) or GRID.

    Attributes:
        text: Affiliation text.
        identifier: Raw identifier value (any source).
        identifier_source: Source of identifier (ROR, GRID, ISNI, etc.).
        email: Extracted email for correspondence authors.
        ror_id: ROR identifier if source is ROR (convenience field).
        grid_id: GRID identifier if source is GRID (convenience field).
    """

    text: str
    identifier: str | None
    identifier_source: str | None
    email: str | None
    ror_id: str | None  # Duplicated from identifier if source == "ROR"
    grid_id: str | None  # Duplicated from identifier if source == "GRID"


class RawAuthor(TypedDict, total=False):
    """Raw author data before normalization."""

    last_name: str | None
    initials: str | None
    fore_name: str | None
    collective_name: str | None
    affiliations: list[str] | None
    structured_affiliations: list[StructuredAffiliation] | None


class AuthorExtractor(BaseFieldExtractor):
    """Extractor for author information from PubMed XML.

    Handles:
    - Individual authors with LastName, Initials/ForeName
    - Collective/group authors
    - Author affiliations (AffiliationInfo)
    - Empty author lists
    """

    def extract(self, element: Element | None) -> list[RawAuthor] | None:
        """Extract raw author data from XML.

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

        raw_authors = [
            self._build_raw_author(author)
            for author in author_list.findall("Author")
        ]

        return raw_authors if raw_authors else None

    def _build_raw_author(self, author: Element) -> RawAuthor:
        """Build one raw author payload from an Author XML element."""
        affiliations, structured_affiliations = self._extract_affiliations(author)
        return RawAuthor(
            last_name=get_text(author.find("LastName")),
            initials=get_text(author.find("Initials")),
            fore_name=get_text(author.find("ForeName")),
            collective_name=get_text(author.find("CollectiveName")),
            affiliations=affiliations if affiliations else None,
            structured_affiliations=(
                structured_affiliations if structured_affiliations else None
            ),
        )

    def _extract_affiliations(
        self,
        author: Element,
    ) -> tuple[list[str], list[StructuredAffiliation]]:
        """Extract legacy and structured affiliations from one author node."""
        affiliations: list[str] = []
        structured_affiliations: list[StructuredAffiliation] = []
        for info in author.findall("AffiliationInfo"):
            aff_text = get_text(info.find("Affiliation"))
            if not aff_text:
                continue
            affiliations.append(aff_text)
            structured_aff = self._extract_structured_affiliation(info)
            if structured_aff:
                structured_affiliations.append(structured_aff)
        return affiliations, structured_affiliations

    def _find_identifier(self, aff_info: Element) -> tuple[str | None, str | None]:
        """Find the best identifier from AffiliationInfo, preferring ROR > GRID > ISNI > RINGGOLD.

        Args:
            aff_info: AffiliationInfo XML element.

        Returns:
            Tuple of (identifier_value, identifier_source) or (None, None).
        """
        for source in ["ROR", "GRID", "ISNI", "RINGGOLD"]:
            for id_elem in aff_info.findall("Identifier"):
                if id_elem.get("Source") == source and id_elem.text:
                    return id_elem.text.strip(), source

        # Fallback: take the first available identifier
        for id_elem in aff_info.findall("Identifier"):
            if id_elem.text:
                return id_elem.text.strip(), id_elem.get("Source")

        return None, None

    def _extract_structured_affiliation(
        self, aff_info: Element
    ) -> StructuredAffiliation | None:
        """Extract structured affiliation from AffiliationInfo element.

        MEDLINE AffiliationInfo structure:
        <AffiliationInfo>
            <Affiliation>University Name, Department, City, Country.
                         Electronic address: email@example.com</Affiliation>
            <Identifier Source="ROR">https://ror.org/...</Identifier>
            <Identifier Source="GRID">grid.12345.6</Identifier>
        </AffiliationInfo>

        Args:
            aff_info: AffiliationInfo XML element.

        Returns:
            StructuredAffiliation dict or None if no text.
        """
        aff_elem = aff_info.find("Affiliation")
        aff_text = get_text(aff_elem)
        if not aff_text:
            return None

        identifier, identifier_source = self._find_identifier(aff_info)

        # Extract email if present in affiliation text
        email = self._extract_email_from_text(aff_text)

        return StructuredAffiliation(
            text=aff_text,
            identifier=identifier,
            identifier_source=identifier_source,
            email=email,
            ror_id=identifier if identifier_source == "ROR" else None,
            grid_id=identifier if identifier_source == "GRID" else None,
        )

    def _extract_email_from_text(self, text: str) -> str | None:
        """Extract email address from affiliation text.

        PubMed affiliations may contain correspondence emails, often marked with
        'Electronic address:' prefix.

        Args:
            text: Affiliation text that may contain email.

        Returns:
            Email address if found, None otherwise.
        """
        match = EMAIL_PATTERN.search(text)
        return match.group(0) if match else None

    def normalize(self, raw_value: object) -> list[str]:
        """Normalize author list into 'LastName, Initials' format.

        Args:
            raw_value: List of raw author dicts.

        Returns:
            List of formatted author names.

        Note:
            This method is still used internally by PubMed transformer for
            backwards compatibility. New code should use the unified service.
        """

        raw_authors = cast("list[RawAuthor]", raw_value)
        authors = []
        for raw in raw_authors:
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
            element: XML element to process.

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

        return sorted(all_affiliations)

    @classmethod
    def parse_structured_affiliations(
        cls, article_node: Element
    ) -> list[StructuredAffiliation]:
        """Extract unique structured affiliations with identifier metadata.

        This method provides enhanced affiliation data including institutional
        identifiers (ROR, GRID) and extracted email addresses for institutional
        bibliometric analysis and author disambiguation.

        Args:
            article_node: The Article element containing AuthorList.

        Returns:
            List of unique StructuredAffiliation dicts, sorted by text.
            Each dict contains:
            - text: Affiliation text
            - identifier: Institutional identifier (if available)
            - identifier_source: Source of identifier (ROR, GRID, etc.)
            - email: Extracted email (if present in text)
        """
        extractor = cls()
        raw_authors = extractor.extract(article_node)
        if not raw_authors:
            return []

        # Use text as key to deduplicate affiliations
        seen_texts: dict[str, StructuredAffiliation] = {}
        for author in raw_authors:
            structured_affs = author.get("structured_affiliations")
            if structured_affs:
                for aff in structured_affs:
                    text = aff.get("text", "")
                    if text and text not in seen_texts:
                        seen_texts[text] = aff

        # Return sorted by text for consistent ordering
        return sorted(seen_texts.values(), key=lambda x: x.get("text", ""))
