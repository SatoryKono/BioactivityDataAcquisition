# mypy: disable-error-code="misc"
"""Pagination metadata model shared across ChEMBL API response modules."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ChemblPageMeta"]


class ChemblPageMeta(BaseModel):
    """Pagination metadata from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    limit: int = Field(description="Number of records per page")
    offset: int = Field(description="Current offset")
    total_count: int = Field(description="Total number of records available")
    next: str | None = Field(default=None, description="Next page URL")
    previous: str | None = Field(default=None, description="Previous page URL")
