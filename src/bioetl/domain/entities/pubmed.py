"""PubMed domain entities.

Contains:
- PubMedPublicationEntity: Domain entity (dataclass) with lineage fields
- ArticleRecord: DTO (Pydantic) for type-safe data transfer at boundaries

DTO Design:
- Uses extra='forbid' to detect API changes early
- frozen=True ensures immutability
- Adapters return DTOs, transformers convert to Domain Entities

Note: PubMedPublicationEntity inherits common fields from PublicationEntityBase.
Provider-specific fields (pmc_id, journal_abbrev, etc.) are defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField

from bioetl.domain.entities.publication_base import PublicationEntityBase

# === Pydantic DTO Model ===


class ArticleRecord(BaseModel):
    """Scientific article DTO from PubMed.

    Represents article metadata extracted from PubMed XML via Entrez API.
    Required field: pmid.

    Example:
        >>> record = ArticleRecord(
        ...     pmid="12345678",
        ...     title="Example Article Title",
        ...     journal="Nature",
        ...     year=2024,
        ... )
        >>> record.model_dump()
        {'pmid': '12345678', 'title': 'Example Article Title', ...}
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    pmid: str = PydanticField(description="PubMed ID")

    # Other identifiers
    doi: str | None = PydanticField(
        default=None, description="Digital Object Identifier"
    )
    pmc_id: str | None = PydanticField(default=None, description="PubMed Central ID")

    # Title and abstract
    title: str | None = PydanticField(default=None, description="Article title")
    abstract: str | None = PydanticField(default=None, description="Abstract text")

    # Journal information
    journal: str | None = PydanticField(default=None, description="Full journal title")
    journal_abbrev: str | None = PydanticField(
        default=None, description="Journal abbreviation (ISO)"
    )
    issn: str | None = PydanticField(default=None, description="ISSN")
    volume: str | None = PydanticField(default=None, description="Volume number")
    issue: str | None = PydanticField(default=None, description="Issue number")
    pages: str | None = PydanticField(
        default=None, description="Page numbers (medline_pgn)"
    )
    first_page: str | None = PydanticField(
        default=None, description="First page (unified)"
    )
    last_page: str | None = PydanticField(
        default=None, description="Last page (unified)"
    )

    # Authors (JSON-serialized list of hashed names for PII compliance)
    # affiliations excluded per user request
    authors: str | None = PydanticField(
        default=None, description="Author names (JSON array, hashed for PII)"
    )

    # Dates (ISO format: YYYY-MM-DD or partial)
    pub_date: str | None = PydanticField(
        default=None, description="Publication date (ISO format)"
    )
    year: int | None = PydanticField(
        default=None, description="Publication year (1800-2100)"
    )
    # Note: accepted_date, received_date, revised_date, epub_date excluded from
    # transformer output per design (PubMed pipeline field exclusions)

    # Classification
    publication_types: list[str] = PydanticField(
        default_factory=list, description="Publication types"
    )
    keywords: list[str] = PydanticField(default_factory=list, description="Keywords")
    mesh_terms: list[str] = PydanticField(
        default_factory=list, description="MeSH terms"
    )

    # Chemical and genetic data
    chemicals: list[str] = PydanticField(
        default_factory=list, description="Chemical substance names from ChemicalList"
    )
    gene_symbols: list[str] = PydanticField(
        default_factory=list, description="Gene symbols from GeneSymbolList"
    )
    databanks: list[dict[str, Any]] = PydanticField(
        default_factory=list,
        description="Data bank references (list of {databank_name, accession_numbers})",
    )

    # Additional metadata
    language: str | None = PydanticField(
        default=None, description="Primary language code"
    )
    country: str | None = PydanticField(
        default=None, description="Country of publication"
    )

    # Raw data for forensic (optional)
    raw_xml: str | None = PydanticField(
        default=None, description="Raw XML content (forensic)"
    )


# === Dataclass Domain Entity ===


@dataclass(frozen=True, kw_only=True)
class PubMedPublicationEntity(PublicationEntityBase):
    """Represents a scientific publication from PubMed.

    Domain entity with lineage fields (run_id, content_hash, etc.).
    Inherits common publication fields from PublicationEntityBase.
    For DTO without lineage, use ArticleRecord.

    Contains comprehensive metadata extracted from PubMed XML via Entrez API.
    See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html

    Inherited from PublicationEntityBase:
        doi, pmid, title, abstract, authors, journal, issn, publisher,
        year, publication_date, citation_count, doc_type, language, is_oa,
        oa_status, _lookup_method, _original_id, source.

    PubMed-specific Attributes:
        pmc_id: PubMed Central ID.
        journal_abbrev: Journal abbreviation (ISO).
        volume: Volume number.
        issue: Issue number.
        pages: Page numbers.
        pub_date: Publication date (ISO format).
        publication_year: Alias for year (legacy field).
        mesh_terms: MeSH terms (list).
        keywords: Keywords (list).
        publication_types: Publication types (list).
        country: Country of publication.

    Note: vernacular_title, accepted_date, received_date, revised_date, epub_date
    are excluded from transformer output per PubMed pipeline design.

    Note: pmid is required for PubMed publications and validated in __post_init__.
    """

    # Override: PMID is REQUIRED for PubMed (base has Optional)
    pmid: str

    # PubMed-specific identifiers (pmc_id is now inherited from PublicationEntityBase)
    # Additional identifiers for cross-referencing with publisher databases
    pii: str | None = None  # Publisher Item Identifier
    mid: str | None = None  # Manuscript ID (PMC submission)
    publisher_id: str | None = None  # Publisher-specific identifier

    # PubMed-specific journal information
    journal_abbrev: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None  # Legacy: medline_pgn format ("123-456")
    # first_page and last_page inherited from PublicationEntityBase

    # PubMed-specific dates (stored as ISO strings YYYY-MM-DD or partial)
    pub_date: str | None = None  # Publication date
    # Note: accepted_date, received_date, revised_date, epub_date excluded from
    # transformer output per design (PubMed pipeline field exclusions)

    # PubMed-specific classification
    publication_types: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)

    # PubMed-specific chemical and genetic data
    chemicals: list[str] = field(default_factory=list)  # ChemicalList/NameOfSubstance
    gene_symbols: list[str] = field(default_factory=list)  # GeneSymbolList
    databanks: list[dict[str, Any]] = field(default_factory=list)  # DataBankList

    # PubMed-specific metadata
    country: str | None = None
    # Note: vernacular_title excluded from transformer output per design
    abstract_structured: bool = False  # Whether abstract has labeled sections (NLM)

    # Additional journal fields (Gold schema forensic retention)
    journal_full_title: str | None = None  # Full journal name (unified with ChEMBL)
    journal_iso_abbrev: str | None = None  # ISO abbreviation (alias for journal_abbrev)
    journal_issn_type: str | None = None  # ISSN type: Print/Electronic/Linking
    nlm_unique_id: str | None = None  # NLM catalog ID
    medline_pgn: str | None = None  # Original PubMed pagination (alias for pages)

    # Additional date fields
    pub_month: int | None = None  # Publication month (1-12)
    pub_day: int | None = None  # Publication day (1-31)
    date_completed: str | None = None  # MEDLINE processing completion date
    date_revised: str | None = None  # Record revision date (MEDLINE)

    # Publication metadata
    publication_status: str | None = None  # ppublish/epublish/aheadofprint
    publication_type_list: str | None = None  # JSON array of pub types
    citation_subset: str | None = None  # Citation subset codes (e.g., 'AIM')

    # Enhanced affiliation data (for institutional analysis)
    structured_affiliations: str | None = None  # JSON array with identifier metadata
    authors_with_affiliations: str | None = (
        None  # JSON array: author-affiliation mapping
    )

    # Denormalized counts (Gold schema)
    author_count: int | None = None
    mesh_heading_count: int | None = None
    keyword_count: int | None = None
    grant_count: int | None = None
    reference_count: int | None = None
    chemical_count: int | None = None

    # Legacy field (kept for backward compatibility)
    publication_year: int | None = None  # Alias for year

    # Override: Default source for PubMed
    _source: str = "pubmed"

    def __post_init__(self) -> None:
        """Post-initialization validation.

        Validates that pmid is provided (required for PubMed publications).
        """
        super().__post_init__()
        if not self.pmid:
            raise ValueError("PubMed Publication PMID is required")


__all__ = ["ArticleRecord", "PubMedPublicationEntity"]
