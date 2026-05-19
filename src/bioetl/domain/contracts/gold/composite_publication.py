# mypy: disable-error-code="misc"
"""Composite publication Gold schema."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._composite_gold_common_schema import (
    CompositeLookupLineageSchema,
)


class CompositePublicationGoldSchema(CompositeLookupLineageSchema):
    """Schema for Composite Publication in Gold layer."""

    entity_id: Series[str] = pa.Field(
        nullable=False,
        description="Stable business identifier for merged publication entity.",
    )

    publication_id: Series[str] = pa.Field(
        nullable=True,
        description="Source ChEMBL publication identifier retained as lineage anchor.",
    )
    doi: Series[str] = pa.Field(
        nullable=True,
        description="Canonical publication DOI used for cross-provider publication joins.",
    )
    pmid: Series[str] = pa.Field(
        nullable=True,
        description="Canonical PubMed identifier used for cross-provider publication joins.",
    )
    pmc_id: Series[str] = pa.Field(
        nullable=True,
        description="Canonical PubMed Central identifier retained for publication lineage.",
    )
    title: Series[str] = pa.Field(
        nullable=False,
        description="Canonical-cleaned publication title retained as fallback join evidence.",
    )
    src_id: Series[int] = pa.Field(
        nullable=True,
        description="Provider source identifier retained as source-scoped lineage metadata.",
    )
