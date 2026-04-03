# mypy: disable-error-code="misc"
"""Internal PubMed ESearch response models."""

from __future__ import annotations

__all__ = ["PubMedSearchResponse", "PubMedSearchResult"]

from pydantic import BaseModel, ConfigDict, Field


class PubMedSearchResult(BaseModel):
    """Result from PubMed ESearch endpoint."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    count: int | None = Field(default=None, description="Total count of results")
    ret_max: int | None = Field(
        default=None, alias="retmax", description="Maximum records to return"
    )
    ret_start: int | None = Field(
        default=None, alias="retstart", description="Starting index"
    )
    id_list: list[str] = Field(
        default_factory=list, alias="idlist", description="List of PMIDs"
    )
    web_env: str | None = Field(
        default=None, alias="webenv", description="Web environment ID"
    )
    query_key: str | None = Field(
        default=None, alias="querykey", description="Query key"
    )


class PubMedSearchResponse(BaseModel):
    """Complete PubMed ESearch API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    esearchresult: PubMedSearchResult | None = Field(
        default=None, description="Search result data"
    )
