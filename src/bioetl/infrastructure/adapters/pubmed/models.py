# mypy: disable-error-code="misc"
"""Pydantic models for PubMed API responses.

These models provide type-safe parsing and validation for PubMed data.
They are infrastructure-layer models (not domain models) for parsed XML records.

Note: PubMed returns XML responses which are parsed by PubMedXmlProcessor.
These models validate the dictionary representation after XML parsing.

Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25499/

See RULES.md §8.2 for JSON response modeling guidelines.
"""

from __future__ import annotations

__all__ = [
    "PubMedArticleId",
    "PubMedArticleRecord",
    "PubMedAuthor",
    "PubMedChemical",
    "PubMedExtendedRecord",
    "PubMedGrant",
    "PubMedJournal",
    "PubMedMeshHeading",
    "PubMedPubDate",
    "PubMedReference",
    "PubMedSearchResponse",
    "PubMedSearchResult",
]


from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.pubmed._search_models import (
    PubMedSearchResponse,
    PubMedSearchResult,
)

# === Basic Record Model (matches current xml_processor output) ===


class PubMedArticleRecord(BaseModel):
    """Basic article record from PubMed XML parsing.

    Matches the output of PubMedXmlProcessor.extract_record().
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    pmid: str | None = Field(default=None, description="PubMed ID")

    # Article Content
    article_title: str = Field(default="No title found", description="Article title")

    # Raw XML for forensic analysis (uses underscore prefix in source data)
    raw_xml: str | None = Field(
        default=None, alias="_raw_xml", description="Raw XML content"
    )


# === Extended Record Model (for comprehensive extraction) ===


class PubMedAuthor(BaseModel):
    """Author information from PubMed."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    last_name: str | None = Field(default=None, description="Author last name")
    fore_name: str | None = Field(default=None, description="Author first name")
    initials: str | None = Field(default=None, description="Author initials")
    affiliation: str | None = Field(default=None, description="Author affiliation")
    collective_name: str | None = Field(
        default=None, description="Collective/organization name"
    )


class PubMedJournal(BaseModel):
    """Journal information from PubMed."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    title: str | None = Field(default=None, description="Full journal title")
    iso_abbreviation: str | None = Field(
        default=None, description="ISO journal abbreviation"
    )
    issn: str | None = Field(default=None, description="ISSN")
    issn_type: str | None = Field(
        default=None, description="ISSN type (Print/Electronic)"
    )
    volume: str | None = Field(default=None, description="Volume number")
    issue: str | None = Field(default=None, description="Issue number")
    country: str | None = Field(default=None, description="Country of publication")
    nlm_unique_id: str | None = Field(default=None, description="NLM unique ID")


class PubMedPubDate(BaseModel):
    """Publication date from PubMed."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    year: int | None = Field(default=None, description="Publication year")
    month: int | str | None = Field(default=None, description="Publication month")
    day: int | None = Field(default=None, description="Publication day")


class PubMedMeshHeading(BaseModel):
    """MeSH heading from PubMed."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    descriptor_name: str | None = Field(default=None, description="MeSH descriptor")
    descriptor_ui: str | None = Field(default=None, description="MeSH descriptor UI")
    major_topic: bool = Field(default=False, description="Is major topic")
    qualifiers: list[JsonDict] | None = (  # Any: untyped API JSON record
        Field(  # Any: nested API JSON has heterogeneous values
            default_factory=list, description="MeSH qualifiers"
        )
    )


class PubMedChemical(BaseModel):
    """Chemical substance from PubMed."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    registry_number: str | None = Field(default=None, description="CAS registry number")
    name: str | None = Field(default=None, description="Substance name")
    ui: str | None = Field(default=None, description="Substance UI")


class PubMedGrant(BaseModel):
    """Grant information from PubMed."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    grant_id: str | None = Field(default=None, description="Grant ID")
    acronym: str | None = Field(default=None, description="Grant acronym")
    agency: str | None = Field(default=None, description="Funding agency")
    country: str | None = Field(default=None, description="Funding country")


class PubMedReference(BaseModel):
    """Reference/citation from PubMed."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    citation: str | None = Field(default=None, description="Reference citation text")
    pmid: str | None = Field(default=None, description="Referenced PMID")


class PubMedArticleId(BaseModel):
    """Article identifier from PubMed."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id_type: str = Field(description="ID type (pubmed, doi, pmc, etc.)")
    value: str = Field(description="ID value")


class PubMedExtendedRecord(BaseModel):
    """Extended article record with full metadata from PubMed.

    Represents a comprehensive extraction of PubMed article data.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    pmid: int = Field(description="PubMed ID")

    # Article Identifiers
    doi: str | None = Field(default=None, description="Digital Object Identifier")
    pmc_id: str | None = Field(default=None, description="PubMed Central ID")
    pii: str | None = Field(default=None, description="Publisher Item Identifier")

    # Article Content
    title: str = Field(description="Article title")
    abstract: str | None = Field(default=None, description="Abstract text")
    abstract_structured: bool = Field(
        default=False, description="Whether abstract has NLM sections"
    )
    vernacular_title: str | None = Field(
        default=None, description="Original non-English title"
    )
    language: str | None = Field(default=None, description="Primary language code")

    # Authors
    authors: list[PubMedAuthor] | None = Field(
        default_factory=list, description="Article authors"
    )
    author_count: int | None = Field(default=None, description="Number of authors")

    # Journal Information
    journal: PubMedJournal | None = Field(
        default=None, description="Journal information"
    )

    # Publication Details
    pub_date: PubMedPubDate | None = Field(default=None, description="Publication date")
    medline_pgn: str | None = Field(
        default=None, description="Page numbers (MEDLINE format)"
    )
    publication_status: str | None = Field(
        default=None, description="Publication status"
    )
    publication_types: list[str] | None = Field(
        default_factory=list, description="Publication types"
    )

    # MeSH Terms
    mesh_headings: list[PubMedMeshHeading] | None = Field(
        default_factory=list, description="MeSH headings"
    )
    mesh_heading_count: int | None = Field(
        default=None, description="Number of MeSH headings"
    )

    # Keywords
    keywords: list[str] | None = Field(default_factory=list, description="Keywords")
    keyword_count: int | None = Field(default=None, description="Number of keywords")

    # Chemicals
    chemicals: list[PubMedChemical] | None = Field(
        default_factory=list, description="Chemical substances"
    )
    chemical_count: int | None = Field(default=None, description="Number of chemicals")

    # Grants
    grants: list[PubMedGrant] | None = Field(
        default_factory=list, description="Grant information"
    )
    grant_count: int | None = Field(default=None, description="Number of grants")

    # References
    references: list[PubMedReference] | None = Field(
        default_factory=list, description="Article references"
    )
    reference_count: int | None = Field(
        default=None, description="Number of references"
    )

    # Dates
    date_completed: str | None = Field(
        default=None, description="MEDLINE processing completion date"
    )
    date_revised: str | None = Field(default=None, description="Record revision date")

    # Citation
    citation_subset: str | None = Field(
        default=None, description="Citation subset codes"
    )

    # Article IDs
    article_ids: list[PubMedArticleId] | None = Field(
        default_factory=list, description="All article identifiers"
    )


# === Record Type Mapping ===

PUBMED_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "publication": PubMedArticleRecord,
    "publication_extended": PubMedExtendedRecord,
}
