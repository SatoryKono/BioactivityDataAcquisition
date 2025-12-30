"""Pydantic models for CrossRef API responses.

These models provide type-safe parsing and validation for CrossRef REST API responses.
They are infrastructure-layer models (not domain models) for raw API data.

Documentation: https://api.crossref.org/swagger-ui/index.html

See RULES.md §8.2 for JSON response modeling guidelines.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# === Shared Models ===


class CrossRefAuthor(BaseModel):
    """Author information from CrossRef."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    given: str | None = Field(default=None, description="Given (first) name")
    family: str | None = Field(default=None, description="Family (last) name")
    name: str | None = Field(default=None, description="Full name (for organizations)")
    suffix: str | None = Field(default=None, description="Name suffix")
    sequence: str | None = Field(
        default=None, description="Author sequence (first, additional)"
    )
    orcid: str | None = Field(
        default=None, alias="ORCID", description="ORCID identifier"
    )
    authenticated_orcid: bool | None = Field(
        default=None,
        alias="authenticated-orcid",
        description="Whether ORCID is authenticated",
    )
    affiliation: list[dict[str, Any]] | None = Field(
        default_factory=list, description="Author affiliations"
    )


class CrossRefFunder(BaseModel):
    """Funder information from CrossRef."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    doi: str | None = Field(default=None, alias="DOI", description="Funder DOI")
    name: str | None = Field(default=None, description="Funder name")
    award: list[str] | None = Field(default_factory=list, description="Award numbers")
    doi_asserted_by: str | None = Field(
        default=None, alias="doi-asserted-by", description="Who asserted the DOI"
    )


class CrossRefLicense(BaseModel):
    """License information from CrossRef."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    url: str | None = Field(default=None, alias="URL", description="License URL")
    content_version: str | None = Field(
        default=None, alias="content-version", description="Content version"
    )
    delay_in_days: int | None = Field(
        default=None, alias="delay-in-days", description="Embargo delay"
    )
    start: dict[str, Any] | None = Field(default=None, description="License start date")


class CrossRefLink(BaseModel):
    """Content link from CrossRef."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    url: str | None = Field(default=None, alias="URL", description="Link URL")
    content_type: str | None = Field(
        default=None, alias="content-type", description="MIME type"
    )
    content_version: str | None = Field(
        default=None, alias="content-version", description="Content version"
    )
    intended_application: str | None = Field(
        default=None, alias="intended-application", description="Intended use"
    )


class CrossRefReference(BaseModel):
    """Reference/citation from CrossRef."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    key: str | None = Field(default=None, description="Reference key")
    doi: str | None = Field(default=None, alias="DOI", description="Reference DOI")
    doi_asserted_by: str | None = Field(
        default=None, alias="doi-asserted-by", description="Who asserted DOI"
    )
    unstructured: str | None = Field(
        default=None, description="Unstructured reference text"
    )
    issue: str | None = Field(default=None, description="Issue")
    first_page: str | None = Field(
        default=None, alias="first-page", description="First page"
    )
    volume: str | None = Field(default=None, description="Volume")
    author: str | None = Field(default=None, description="First author")
    year: str | None = Field(default=None, description="Publication year")
    journal_title: str | None = Field(
        default=None, alias="journal-title", description="Journal title"
    )
    article_title: str | None = Field(
        default=None, alias="article-title", description="Article title"
    )


class CrossRefAssertion(BaseModel):
    """Publisher assertion from CrossRef."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str | None = Field(default=None, description="Assertion name")
    value: str | None = Field(default=None, description="Assertion value")
    label: str | None = Field(default=None, description="Assertion label")
    group: dict[str, Any] | None = Field(default=None, description="Assertion group")


class CrossRefClinicalTrial(BaseModel):
    """Clinical trial number from CrossRef."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    clinical_trial_number: str | None = Field(
        default=None, alias="clinical-trial-number", description="Trial number"
    )
    registry: str | None = Field(default=None, description="Trial registry")
    type: str | None = Field(default=None, description="Trial type")


class CrossRefDateParts(BaseModel):
    """Date representation from CrossRef (date-parts format)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    date_parts: list[list[int]] | None = Field(
        default=None, alias="date-parts", description="Date parts [[year, month, day]]"
    )
    date_time: str | None = Field(
        default=None, alias="date-time", description="ISO date-time string"
    )
    timestamp: int | None = Field(
        default=None, description="Unix timestamp in milliseconds"
    )


# === Work Record Model ===


class CrossRefWorkRecord(BaseModel):
    """Individual work record from CrossRef API.

    Represents a publication (article, book, dataset, etc.) with DOI.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Identifier
    doi: str = Field(alias="DOI", description="Digital Object Identifier")

    # Type
    type: str = Field(description="Work type (journal-article, book-chapter, etc.)")
    subtype: str | None = Field(default=None, description="Work subtype")

    # Titles
    title: list[str] | None = Field(default_factory=list, description="Work titles")
    subtitle: list[str] | None = Field(default_factory=list, description="Subtitles")
    short_title: list[str] | None = Field(
        default_factory=list, alias="short-title", description="Short titles"
    )
    original_title: list[str] | None = Field(
        default_factory=list, alias="original-title", description="Original titles"
    )

    # Container (Journal/Book)
    container_title: list[str] | None = Field(
        default_factory=list, alias="container-title", description="Container title"
    )
    short_container_title: list[str] | None = Field(
        default_factory=list,
        alias="short-container-title",
        description="Short container title",
    )
    publisher: str | None = Field(default=None, description="Publisher name")
    publisher_location: str | None = Field(
        default=None, alias="publisher-location", description="Publisher location"
    )

    # Identifiers
    issn: list[str] | None = Field(
        default_factory=list, alias="ISSN", description="ISSNs"
    )
    isbn: list[str] | None = Field(
        default_factory=list, alias="ISBN", description="ISBNs"
    )
    prefix: str | None = Field(default=None, description="DOI prefix")
    member: str | None = Field(default=None, description="Member ID")
    source: str | None = Field(default=None, description="Source system")

    # Volume/Issue/Pages
    volume: str | None = Field(default=None, description="Volume")
    issue: str | None = Field(default=None, description="Issue")
    page: str | None = Field(default=None, description="Page range")
    article_number: str | None = Field(
        default=None, alias="article-number", description="Article number"
    )

    # Authors/Editors
    author: list[CrossRefAuthor] | None = Field(
        default_factory=list, description="Authors"
    )
    editor: list[CrossRefAuthor] | None = Field(
        default_factory=list, description="Editors"
    )
    chair: list[CrossRefAuthor] | None = Field(
        default_factory=list, description="Chairs"
    )
    translator: list[CrossRefAuthor] | None = Field(
        default_factory=list, description="Translators"
    )

    # Dates
    issued: CrossRefDateParts | None = Field(
        default=None, description="Publication date"
    )
    published_print: CrossRefDateParts | None = Field(
        default=None, alias="published-print", description="Print publication date"
    )
    published_online: CrossRefDateParts | None = Field(
        default=None, alias="published-online", description="Online publication date"
    )
    created: CrossRefDateParts | None = Field(
        default=None, description="Record creation date"
    )
    deposited: CrossRefDateParts | None = Field(
        default=None, description="Last deposit date"
    )
    indexed: CrossRefDateParts | None = Field(
        default=None, description="Last index date"
    )

    # Content
    abstract: str | None = Field(default=None, description="Abstract text")
    language: str | None = Field(default=None, description="Language code")
    subject: list[str] | None = Field(default_factory=list, description="Subject areas")

    # Funding
    funder: list[CrossRefFunder] | None = Field(
        default_factory=list, description="Funders"
    )

    # License
    license: list[CrossRefLicense] | None = Field(
        default_factory=list, description="Licenses"
    )

    # Links
    link: list[CrossRefLink] | None = Field(
        default_factory=list, description="Content links"
    )

    # Relations
    relation: dict[str, Any] | None = Field(default=None, description="Related works")
    update_to: list[dict[str, Any]] | None = Field(
        default_factory=list, alias="update-to", description="Updates to other works"
    )
    updated_by: list[dict[str, Any]] | None = Field(
        default_factory=list, alias="updated-by", description="Works updating this one"
    )

    # References
    reference: list[CrossRefReference] | None = Field(
        default_factory=list, description="References/bibliography"
    )
    references_count: int | None = Field(
        default=None, alias="references-count", description="Reference count"
    )

    # Citations
    is_referenced_by_count: int | None = Field(
        default=None, alias="is-referenced-by-count", description="Citation count"
    )

    # Clinical Trials
    clinical_trial_number: list[CrossRefClinicalTrial] | None = Field(
        default_factory=list,
        alias="clinical-trial-number",
        description="Clinical trial numbers",
    )

    # Assertions
    assertion: list[CrossRefAssertion] | None = Field(
        default_factory=list, description="Publisher assertions"
    )

    # Scores
    score: float | None = Field(default=None, description="Search relevance score")

    # Standards Bodies
    standards_body: list[dict[str, Any]] | None = Field(
        default_factory=list, alias="standards-body", description="Standards bodies"
    )

    # Update Policy
    update_policy: str | None = Field(
        default=None, alias="update-policy", description="Update policy DOI"
    )


# === API Response Models ===


class CrossRefMessage(BaseModel):
    """Message wrapper for CrossRef API responses."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Facets
    facets: dict[str, Any] | None = Field(default=None, description="Search facets")

    # Pagination
    total_results: int | None = Field(
        default=None, alias="total-results", description="Total result count"
    )
    items_per_page: int | None = Field(
        default=None, alias="items-per-page", description="Items per page"
    )
    query: dict[str, Any] | None = Field(default=None, description="Query information")

    # Cursor
    next_cursor: str | None = Field(
        default=None, alias="next-cursor", description="Next cursor"
    )

    # Items (for list responses)
    items: list[CrossRefWorkRecord] | None = Field(
        default_factory=list, description="Work records"
    )


class CrossRefWorksResponse(BaseModel):
    """Complete CrossRef works API response (list endpoint)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    status: str = Field(description="Response status")
    message_type: str = Field(alias="message-type", description="Message type")
    message_version: str | None = Field(
        default=None, alias="message-version", description="API version"
    )
    message: CrossRefMessage = Field(description="Response message")


class CrossRefWorkResponse(BaseModel):
    """Complete CrossRef work API response (single work endpoint)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    status: str = Field(description="Response status")
    message_type: str = Field(alias="message-type", description="Message type")
    message_version: str | None = Field(
        default=None, alias="message-version", description="API version"
    )
    message: CrossRefWorkRecord = Field(description="Work record")


# === Record Type Mapping ===

CROSSREF_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "work": CrossRefWorkRecord,
    "publication": CrossRefWorkRecord,
}
