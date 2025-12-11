"""Publication domain entity.

Represents a scientific publication or document from ChEMBL database.
A Publication is a literature reference that is the source of bioactivity data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from bioetl.domain.entities.base import EntityBase, extract_field
from bioetl.domain.value_objects import ChemblId


@dataclass(frozen=True)
class Publication(EntityBase):
    """Domain entity representing a scientific publication.

    A Publication encapsulates information about the literature source
    of bioactivity data, including journal details and identifiers.

    Attributes:
        document_chembl_id: Unique ChEMBL document identifier (primary key).
        doc_type: Type of document (PUBLICATION, DATASET, PATENT, OTHER).
        title: Document title.
        journal: Abbreviated journal name.
        year: Publication year.
        doi: Digital Object Identifier.
        pubmed_id: PubMed identifier.

    Business Key:
        The business key is (document_chembl_id) as it's the unique identifier.

    Example:
        >>> pub = Publication.from_record({
        ...     'document_chembl_id': 'CHEMBL1123081',
        ...     'doc_type': 'PUBLICATION',
        ...     'title': 'Novel kinase inhibitors...',
        ...     'journal': 'J Med Chem',
        ...     'year': 2020,
        ... })
    """

    # Primary identifier
    document_chembl_id: str

    # Document classification
    doc_type: str

    # Bibliographic information
    title: str | None = None
    abstract: str | None = None
    authors: str | None = None
    journal: str | None = None
    journal_full_title: str | None = None
    volume: str | None = None
    issue: str | None = None
    first_page: str | None = None
    last_page: str | None = None
    year: int | None = None

    # External identifiers
    doi: str | None = None
    pubmed_id: str | None = None
    patent_id: str | None = None

    # ChEMBL-specific
    doi_chembl: str | None = None
    chembl_release: str | None = None
    contact: str | None = None

    # Source information
    src_id: int | None = None

    # Search relevance
    score: float | None = None

    # Class configuration
    BUSINESS_KEY_FIELDS: ClassVar[tuple[str, ...]] = ("document_chembl_id",)
    PRIMARY_KEY_FIELD: ClassVar[str] = "document_chembl_id"

    def __post_init__(self) -> None:
        """Validate entity invariants."""
        # Validate ChEMBL ID format
        if not self.document_chembl_id.startswith("CHEMBL"):
            raise ValueError(
                f"Invalid document_chembl_id format: {self.document_chembl_id}"
            )

        # Validate doc_type
        allowed_doc_types = {"PUBLICATION", "DATASET", "PATENT", "OTHER"}
        if self.doc_type not in allowed_doc_types:
            raise ValueError(
                f"Invalid doc_type: {self.doc_type}. "
                f"Must be one of: {allowed_doc_types}"
            )

    @property
    def chembl_id(self) -> ChemblId:
        """Return document ID as ChemblId value object."""
        return ChemblId(self.document_chembl_id)

    @property
    def is_publication(self) -> bool:
        """Check if this is a journal publication."""
        return self.doc_type == "PUBLICATION"

    @property
    def is_patent(self) -> bool:
        """Check if this is a patent."""
        return self.doc_type == "PATENT"

    @property
    def is_dataset(self) -> bool:
        """Check if this is a deposited dataset."""
        return self.doc_type == "DATASET"

    @property
    def has_pubmed(self) -> bool:
        """Check if publication has PubMed ID."""
        return self.pubmed_id is not None

    @property
    def has_doi(self) -> bool:
        """Check if publication has DOI."""
        return self.doi is not None

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Publication":
        """Create Publication from raw record dictionary.

        Args:
            record: Dictionary from API response or database.

        Returns:
            Publication entity instance.

        Raises:
            ValueError: If required fields are missing.
        """
        return cls(
            # Required fields
            document_chembl_id=extract_field(
                record, "document_chembl_id", required=True
            ),
            doc_type=extract_field(record, "doc_type", required=True),
            # Bibliographic
            title=extract_field(record, "title"),
            abstract=extract_field(record, "abstract"),
            authors=extract_field(record, "authors"),
            journal=extract_field(record, "journal"),
            journal_full_title=extract_field(record, "journal_full_title"),
            volume=extract_field(record, "volume"),
            issue=extract_field(record, "issue"),
            first_page=extract_field(record, "first_page"),
            last_page=extract_field(record, "last_page"),
            year=extract_field(record, "year", coerce=int),
            # Identifiers
            doi=extract_field(record, "doi"),
            pubmed_id=extract_field(record, "pubmed_id"),
            patent_id=extract_field(record, "patent_id"),
            # ChEMBL
            doi_chembl=extract_field(record, "doi_chembl"),
            chembl_release=extract_field(record, "chembl_release"),
            contact=extract_field(record, "contact"),
            # Source
            src_id=extract_field(record, "src_id", coerce=int),
            # Score
            score=extract_field(record, "score", coerce=float),
        )


__all__ = ["Publication"]
