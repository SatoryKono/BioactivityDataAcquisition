# mypy: disable-error-code="misc"
"""Semantic Scholar publication schema for Gold contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._publication_common_schema import (
    PublicationGoldCommonSchema,
)
from bioetl.domain.schemas.common.publication_base import (
    OA_STATUS_VALUES,
)


class SemanticScholarPublicationGoldSchema(PublicationGoldCommonSchema):
    """Schema for Semantic Scholar publication in Gold layer."""

    paper_id: Series[str] = pa.Field(nullable=False)
    corpus_id: Series[float] = pa.Field(nullable=True, coerce=True)
    tldr: Series[str] = pa.Field(nullable=True)
    page_range: Series[str] = pa.Field(nullable=True)
    citations_received: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    influential_citation_count: Series[float] = pa.Field(
        nullable=True,
        ge=0,
        coerce=True,
    )
    is_oa: Series[bool] = pa.Field(nullable=True, coerce=True)
    open_access_url: Series[str] = pa.Field(nullable=True)
    oa_status: Series[str] = pa.Field(nullable=True, isin=OA_STATUS_VALUES)
    subject_fields: Series[str] = pa.Field(nullable=True)
    publication_types: Series[str] = pa.Field(nullable=True)
    citation_contexts: Series[str] = pa.Field(nullable=True)
    author_keys: Series[str] = pa.Field(nullable=True)
    author_s2_ids: Series[str] = pa.Field(nullable=True)
    author_orcids: Series[str] = pa.Field(nullable=True)
    author_h_indices: Series[str] = pa.Field(nullable=True)
    dblp_id: Series[str] = pa.Field(nullable=True)


__all__ = ["SemanticScholarPublicationGoldSchema"]
