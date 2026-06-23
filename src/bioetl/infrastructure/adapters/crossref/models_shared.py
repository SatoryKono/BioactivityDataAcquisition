# mypy: disable-error-code="misc"
"""Shared Pydantic models for CrossRef API payload fragments."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict


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
    affiliation: list[JsonDict] | None = Field(
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
    start: JsonDict | None = Field(default=None, description="License start date")


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
    group: JsonDict | None = Field(default=None, description="Assertion group")


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


__all__ = [
    "CrossRefAssertion",
    "CrossRefAuthor",
    "CrossRefClinicalTrial",
    "CrossRefDateParts",
    "CrossRefFunder",
    "CrossRefLicense",
    "CrossRefLink",
    "CrossRefReference",
]
