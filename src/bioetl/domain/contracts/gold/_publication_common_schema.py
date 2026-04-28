# mypy: disable-error-code="misc"
"""Shared Pandera field blocks for publication-oriented Gold contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._strict_gold_contract_schema import (
    StrictGoldContractSchema,
)
from bioetl.domain.schemas.common.publication_base import LOOKUP_METHODS
from bioetl.domain.validation import DOI_REGEX_PATTERN


class PublicationGoldCommonSchema(StrictGoldContractSchema):
    """Common contract fields shared by provider-specific Gold publication schemas."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    doi: Series[str] = pa.Field(nullable=True, str_matches=DOI_REGEX_PATTERN)
    pmid: Series[str] = pa.Field(nullable=True)
    pmc_id: Series[str] = pa.Field(nullable=True)
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    authors: Series[str] = pa.Field(nullable=True)
    affiliation_list: Series[str] = pa.Field(nullable=True)
    journal: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    page_first: Series[str] = pa.Field(nullable=True)
    page_last: Series[str] = pa.Field(nullable=True)
    publication_year: Series[float] = pa.Field(
        nullable=True,
        ge=1500,
        le=2100,
        coerce=True,
    )
    publication_date: Series[str] = pa.Field(nullable=True)
    publication_type: Series[str] = pa.Field(nullable=True)
    publication_type_unified: Series[str] = pa.Field(nullable=True)
    publication_subclass: Series[str] = pa.Field(nullable=True)
    publication_class: Series[str] = pa.Field(nullable=True)
    citations_made: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    source: Series[str] = pa.Field(nullable=False, alias="_source")
    lookup_method: Series[str] = pa.Field(
        nullable=False,
        alias="_lookup_method",
        isin=LOOKUP_METHODS,
    )
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")


__all__ = ["PublicationGoldCommonSchema"]
