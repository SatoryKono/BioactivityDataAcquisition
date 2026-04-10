# mypy: disable-error-code="misc"
"""CrossRef publication schema for Gold contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import LOOKUP_METHODS
from bioetl.domain.validation import DOI_REGEX_PATTERN


class CrossRefPublicationGoldSchema(pa.DataFrameModel):
    """Schema for CrossRef publication in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    doi: Series[str] = pa.Field(nullable=False, str_matches=DOI_REGEX_PATTERN)
    pmid: Series[str] = pa.Field(nullable=True)
    pmc_id: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    affiliation_list: Series[str] = pa.Field(nullable=True)
    title: Series[str] = pa.Field(nullable=True)
    authors: Series[str] = pa.Field(nullable=True)
    journal: Series[str] = pa.Field(nullable=True)
    issn: Series[str] = pa.Field(nullable=True)
    issn_list: Series[str] = pa.Field(nullable=True)
    publisher: Series[str] = pa.Field(nullable=True)
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
    published_print: Series[str] = pa.Field(nullable=True)
    published_online: Series[str] = pa.Field(nullable=True)
    publication_type: Series[str] = pa.Field(nullable=True)
    publication_type_unified: Series[str] = pa.Field(nullable=True)
    publication_subclass: Series[str] = pa.Field(nullable=True)
    publication_class: Series[str] = pa.Field(nullable=True)
    citations_received: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    citations_made: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    language: Series[str] = pa.Field(nullable=True)
    license_url: Series[str] = pa.Field(nullable=True)
    subject_keywords: Series[str] = pa.Field(nullable=True)
    content_domain_domains: Series[str] = pa.Field(nullable=True)
    content_domain_crossmark_restriction: Series[bool] = pa.Field(
        nullable=True,
        coerce=True,
    )
    alternative_id: Series[str] = pa.Field(nullable=True)
    published: Series[str] = pa.Field(nullable=True)
    journal_name_short: Series[str] = pa.Field(nullable=True)
    issn_print: Series[str] = pa.Field(nullable=True)
    issn_electronic: Series[str] = pa.Field(nullable=True)
    author_keys: Series[str] = pa.Field(nullable=True)
    author_orcids: Series[str] = pa.Field(nullable=True)
    author_details: Series[str] = pa.Field(nullable=True)
    references: Series[str] = pa.Field(nullable=True)
    source: Series[str] = pa.Field(nullable=False, alias="_source")
    lookup_method: Series[str] = pa.Field(
        nullable=False,
        alias="_lookup_method",
        isin=LOOKUP_METHODS,
    )
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


__all__ = ["CrossRefPublicationGoldSchema"]
