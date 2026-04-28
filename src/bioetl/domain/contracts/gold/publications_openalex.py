# mypy: disable-error-code="misc"
"""OpenAlex publication schema for Gold contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._publication_common_schema import (
    PublicationGoldCommonSchema,
)
from bioetl.domain.schemas.common.publication_base import (
    OA_STATUS_VALUES,
)


class OpenAlexPublicationGoldSchema(PublicationGoldCommonSchema):
    """Schema for OpenAlex publication in Gold layer."""

    openalex_id: Series[str] = pa.Field(nullable=False)
    subject_mesh: Series[str] = pa.Field(nullable=True)
    subject_keywords: Series[str] = pa.Field(nullable=True)
    mag_id: Series[str] = pa.Field(nullable=True)
    issn: Series[str] = pa.Field(nullable=True)
    publisher: Series[str] = pa.Field(nullable=True)
    is_oa: Series[bool] = pa.Field(nullable=True, coerce=True)
    oa_status: Series[str] = pa.Field(nullable=True, isin=OA_STATUS_VALUES)
    is_retracted: Series[bool] = pa.Field(nullable=False, coerce=True)
    citations_received: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    language: Series[str] = pa.Field(nullable=True)
    fwci: Series[float] = pa.Field(nullable=True, ge=0)
    subject_topics: Series[str] = pa.Field(nullable=True)
    primary_topic: Series[str] = pa.Field(nullable=True)
    grants: Series[str] = pa.Field(nullable=True)
    institution_ids: Series[str] = pa.Field(nullable=True)
    institution_country_codes: Series[str] = pa.Field(nullable=True)
    ror_ids: Series[str] = pa.Field(nullable=True)
    author_keys: Series[str] = pa.Field(nullable=True)
    author_openalex_ids: Series[str] = pa.Field(nullable=True)
    author_orcids: Series[str] = pa.Field(nullable=True)


__all__ = ["OpenAlexPublicationGoldSchema"]
