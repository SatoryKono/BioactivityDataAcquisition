# mypy: disable-error-code="misc"
"""CrossRef publication schema for Gold contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._publication_common_schema import (
    PublicationGoldCommonSchema,
)
from bioetl.domain.validation import DOI_REGEX_PATTERN


class CrossRefPublicationGoldSchema(PublicationGoldCommonSchema):
    """Schema for CrossRef publication in Gold layer."""

    doi: Series[str] = pa.Field(nullable=False, str_matches=DOI_REGEX_PATTERN)
    issn: Series[str] = pa.Field(nullable=True)
    issn_list: Series[str] = pa.Field(nullable=True)
    publisher: Series[str] = pa.Field(nullable=True)
    published_print: Series[str] = pa.Field(nullable=True)
    published_online: Series[str] = pa.Field(nullable=True)
    citations_received: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
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


__all__ = ["CrossRefPublicationGoldSchema"]
