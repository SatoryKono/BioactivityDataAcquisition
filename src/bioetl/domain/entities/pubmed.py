# mypy: disable-error-code="misc"
"""PubMed domain entities.

Contains:
- PubMedPublicationEntity: Domain entity (dataclass) with lineage fields
- ArticleRecord: DTO (Pydantic) for type-safe data transfer at boundaries

DTO Design:
- Uses extra='forbid' to detect API changes early
- frozen=True ensures immutability
- Adapters return DTOs, transformers convert to Domain Entities

Note: PubMedPublicationEntity inherits common fields from PublicationEntityBase.
Provider-specific fields (pmc_id, journal_name_short, etc.) are defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField

from bioetl.domain._immutability import freeze_fields
from bioetl.domain.entities.publication_base import PublicationEntityBase
from bioetl.domain.types import JsonDict

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
        default=None, description="Publication year (1500-2100)"
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
    databanks: list[JsonDict] = PydanticField(
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
        journal_name: Full journal title (unified field name).
        journal_name_short: Journal abbreviation (unified field name).
        volume: Volume number.
        issue: Issue number.
        page_range: Page numbers.
        pub_date: Publication date (ISO format).
        publication_year: Alias for year (legacy field).
        subject_mesh: MeSH terms (list).
        subject_keywords: Keywords (list).
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
    journal: str | None = None
    journal_name_short: str | None = None
    volume: str | None = None
    issue: str | None = None
    page_range: str | None = None  # Unified page range (e.g., "123-456")
    # first_page and last_page inherited from PublicationEntityBase

    # PubMed-specific dates (stored as ISO strings YYYY-MM-DD or partial)
    pub_date: str | None = None  # Publication date
    # Note: accepted_date, received_date, revised_date, epub_date excluded from
    # transformer output per design (PubMed pipeline field exclusions)

    # PubMed-specific classification
    publication_types: list[str] = field(default_factory=list)
    subject_keywords: list[str] = field(default_factory=list)
    subject_mesh: list[str] = field(default_factory=list)

    # PubMed-specific chemical and genetic data
    chemicals: list[str] = field(default_factory=list)  # ChemicalList/NameOfSubstance
    gene_symbols: list[str] = field(default_factory=list)  # GeneSymbolList
    databanks: list[JsonDict] = field(default_factory=list)  # DataBankList

    # PubMed-specific metadata
    country: str | None = None
    # Note: vernacular_title excluded from transformer output per design
    abstract_structured: bool = False  # Whether abstract has labeled sections (NLM)

    # Additional journal fields (Gold schema forensic retention)
    journal_iso_abbrev: str | None = (
        None  # ISO abbreviation (alias for journal_name_short)
    )
    journal_issn_type: str | None = None  # ISSN type: Print/Electronic/Linking
    nlm_unique_id: str | None = None  # NLM catalog ID
    medline_pgn: str | None = None  # Original PubMed pagination (alias for page_range)

    # Additional date fields
    pub_month: int | None = None  # Publication month (1-12)
    pub_day: int | None = None  # Publication day (1-31)
    date_completed: str | None = None  # MEDLINE processing completion date
    date_revised: str | None = None  # Record revision date (MEDLINE)

    # Publication metadata
    publication_status: str | None = None  # ppublish/epublish/aheadofprint
    citation_subset: str | None = None  # Citation subset codes (e.g., 'AIM')

    # Enhanced affiliation data (for institutional analysis)
    affiliation_structured: str | None = None  # JSON array with identifier metadata
    authors_with_affiliations: str | None = (
        None  # JSON array: author-affiliation mapping
    )

    # Denormalized counts (Gold schema)
    author_count: int | None = None
    mesh_heading_count: int | None = None
    keyword_count: int | None = None
    grant_count: int | None = None
    chemical_count: int | None = None

    # Override: Default source for PubMed
    _source: str = "pubmed"

    def __post_init__(self) -> None:
        super().__post_init__()
        freeze_fields(
            self,
            (
                "publication_types",
                "subject_keywords",
                "subject_mesh",
                "chemicals",
                "gene_symbols",
                "databanks",
            ),
        )

    def _validate_invariants(self) -> None:
        """Validate PubMed-specific publication invariants."""
        super()._validate_invariants()
        if not self.pmid:
            raise ValueError("PubMed Publication PMID is required")


__all__ = ["ArticleRecord", "PubMedPublicationEntity"]
