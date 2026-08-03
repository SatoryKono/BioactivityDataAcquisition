# mypy: disable-error-code="misc"
# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
"""Response wrapper models for CrossRef API payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.crossref.models import CrossRefPublicationRecord


class CrossRefMessage(BaseModel):
    """Message wrapper for CrossRef API responses."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    facets: JsonDict | None = Field(
        default=None, description="Search facets"
    )  # Any: nested Crossref JSON with provider-specific schema
    total_results: int | None = Field(
        default=None, alias="total-results", description="Total result count"
    )
    items_per_page: int | None = Field(
        default=None, alias="items-per-page", description="Items per page"
    )
    query: JsonDict | None = Field(
        default=None, description="Query information"
    )  # Any: nested Crossref JSON with provider-specific schema
    next_cursor: str | None = Field(
        default=None, alias="next-cursor", description="Next cursor"
    )
    items: list[CrossRefPublicationRecord] | None = Field(
        default_factory=list, description="Publication records"
    )


class CrossRefPublicationsResponse(BaseModel):
    """Complete CrossRef publications API response (list endpoint)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    status: str = Field(description="Response status")
    message_type: str = Field(alias="message-type", description="Message type")
    message_version: str | None = Field(
        default=None, alias="message-version", description="API version"
    )
    message: CrossRefMessage = Field(description="Response message")


class CrossRefPublicationResponse(BaseModel):
    """Complete CrossRef publication API response (single publication endpoint)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    status: str = Field(description="Response status")
    message_type: str = Field(alias="message-type", description="Message type")
    message_version: str | None = Field(
        default=None, alias="message-version", description="API version"
    )
    message: CrossRefPublicationRecord = Field(description="Publication record")


__all__ = [
    "CrossRefMessage",
    "CrossRefPublicationResponse",
    "CrossRefPublicationsResponse",
]
