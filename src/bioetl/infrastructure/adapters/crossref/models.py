# mypy: disable-error-code="misc"
"""Pydantic models for CrossRef API responses.

These models provide type-safe parsing and validation for CrossRef REST API responses.
They are infrastructure-layer models (not domain models) for raw API data.

Documentation: https://api.crossref.org/swagger-ui/index.html

See RULES.md §8.2 for JSON response modeling guidelines.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.crossref.models_shared import (
    CrossRefAssertion,
    CrossRefAuthor,
    CrossRefClinicalTrial,
    CrossRefDateParts,
    CrossRefFunder,
    CrossRefLicense,
    CrossRefLink,
    CrossRefReference,
)

if TYPE_CHECKING:
    import bioetl.infrastructure.adapters.crossref._response_models as _crossref_response_models

__all__ = [
    "CROSSREF_RECORD_MODELS",
    "CrossRefAssertion",
    "CrossRefAuthor",
    "CrossRefClinicalTrial",
    "CrossRefDateParts",
    "CrossRefFunder",
    "CrossRefLicense",
    "CrossRefLink",
    "CrossRefMessage",
    "CrossRefPublicationRecord",
    "CrossRefPublicationResponse",
    "CrossRefPublicationsResponse",
    "CrossRefReference",
]

CrossRefMessage: type[_crossref_response_models.CrossRefMessage]
CrossRefPublicationResponse: type[_crossref_response_models.CrossRefPublicationResponse]
CrossRefPublicationsResponse: type[
    _crossref_response_models.CrossRefPublicationsResponse
]


# === Publication Record Model ===
class CrossRefPublicationRecord(BaseModel):
    """Individual publication record from CrossRef API.

    Represents a scholarly publication (article, book, dataset, etc.) with DOI.

    Terminology:
    - Uses "Publication" instead of CrossRef API term "Work" for Ubiquitous Language
    - Business analysts can understand the model without knowing CrossRef API specifics
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Identifier
    doi: str = Field(alias="DOI", description="Digital Object Identifier")

    # Type (CrossRef API type field - kept as-is for API compatibility)
    type: str = Field(
        description="Publication type (journal-article, book-chapter, etc.)"
    )
    subtype: str | None = Field(default=None, description="Publication subtype")

    # Titles
    title: list[str] | None = Field(
        default_factory=list, description="Publication titles"
    )
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
    relation: JsonDict | None = Field(
        default=None, description="Related works"
    )  # Any: nested Crossref JSON with provider-specific schema
    update_to: list[JsonDict] | None = Field(
        default_factory=list,
        alias="update-to",
        description="Updates to other works",
    )  # Any: nested Crossref JSON with provider-specific schema
    updated_by: list[JsonDict] | None = Field(
        default_factory=list,
        alias="updated-by",
        description="Works updating this one",
    )  # Any: nested Crossref JSON with provider-specific schema

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
    standards_body: list[JsonDict] | None = Field(
        default_factory=list,
        alias="standards-body",
        description="Standards bodies",
    )  # Any: nested Crossref JSON with provider-specific schema

    # Update Policy
    update_policy: str | None = Field(
        default=None, alias="update-policy", description="Update policy DOI"
    )


# === Record Type Mapping ===
CROSSREF_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "work": CrossRefPublicationRecord,
    "publication": CrossRefPublicationRecord,
}

# Load response wrappers only after CrossRefPublicationRecord exists.
_response_models = importlib.import_module(
    "bioetl.infrastructure.adapters.crossref._response_models"
)
CrossRefMessage = _response_models.CrossRefMessage
CrossRefPublicationResponse = _response_models.CrossRefPublicationResponse
CrossRefPublicationsResponse = _response_models.CrossRefPublicationsResponse
_record_namespace = {
    "Any": Any,
    "CrossRefPublicationRecord": CrossRefPublicationRecord,
    "JsonDict": JsonDict,
}
CrossRefMessage.model_rebuild(_types_namespace=_record_namespace)
CrossRefPublicationResponse.model_rebuild(_types_namespace=_record_namespace)
