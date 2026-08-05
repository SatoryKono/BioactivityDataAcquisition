# mypy: disable-error-code="misc"
"""Extended PubMed article record model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.infrastructure.adapters.pubmed._article_components import (
    PubMedArticleId,
    PubMedAuthor,
    PubMedChemical,
    PubMedGrant,
    PubMedJournal,
    PubMedMeshHeading,
    PubMedPubDate,
    PubMedReference,
)

__all__ = ["PubMedExtendedRecord"]


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
