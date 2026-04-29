# mypy: disable-error-code="misc"
"""Shared Pandera field blocks for publication-oriented Gold contracts."""

from __future__ import annotations

from typing import cast

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._strict_gold_contract_schema import (
    StrictGoldContractSchema,
)
from bioetl.domain.mapping.publication_type_classification import (
    publication_classification_values,
)
from bioetl.domain.schemas.common.publication_base import LOOKUP_METHODS
from bioetl.domain.validation import DOI_REGEX_PATTERN


def _check_classification_values(
    series: Series[str],
    *,
    field_name: str,
) -> Series[bool]:
    allowed = publication_classification_values(field_name)
    if not allowed:
        return cast(Series[bool], series.isna() | series.notna())
    return cast(Series[bool], series.isna() | series.isin(allowed))


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

    @pa.check("publication_type_unified", name="publication_type_unified_taxonomy")
    def _check_publication_type_unified(cls, series: Series[str]) -> Series[bool]:
        """Validate derived unified publication type against loaded taxonomy."""
        return _check_classification_values(
            series,
            field_name="publication_type_unified",
        )

    @pa.check("publication_subclass", name="publication_subclass_taxonomy")
    def _check_publication_subclass(cls, series: Series[str]) -> Series[bool]:
        """Validate derived publication subclass against loaded taxonomy."""
        return _check_classification_values(series, field_name="publication_subclass")

    @pa.check("publication_class", name="publication_class_taxonomy")
    def _check_publication_class(cls, series: Series[str]) -> Series[bool]:
        """Validate derived publication class against loaded taxonomy."""
        return _check_classification_values(series, field_name="publication_class")


__all__ = ["PublicationGoldCommonSchema"]
