# mypy: disable-error-code="misc"
"""Shared base schema for composite Gold-layer contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class CompositeGoldCommonSchema(pa.DataFrameModel):
    """Common composite Gold output fields across merged entity families."""

    entity_id: Series[str] = pa.Field(nullable=False)
    source: Series[str] = pa.Field(
        nullable=True,
        alias="_source",
        description="Source-family lineage marker retained as composite metadata.",
    )
    dq_warn: Series[bool] = pa.Field(
        nullable=False,
        default=False,
        alias="_dq_warn",
        description="Soft data-quality warning flag.",
    )
    dq_error: Series[bool] = pa.Field(
        nullable=False,
        default=False,
        alias="_dq_error",
        description="Hard data-quality error flag.",
    )
    index: Series[int] = pa.Field(nullable=False, alias="_index")
    source_providers: Series[str] = pa.Field(nullable=False, alias="_source_providers")
    enrichment_status: Series[str] = pa.Field(
        nullable=False, alias="_enrichment_status"
    )

    class Config:
        """Pandera configuration for composite outputs."""

        strict = True
        coerce = True


class CompositeLookupLineageSchema(CompositeGoldCommonSchema):
    """Composite schema mixin for provider lookup lineage metadata."""

    lookup_method: Series[str] = pa.Field(
        nullable=True,
        alias="_lookup_method",
        description="Lookup strategy retained as inherited provider/composite lineage metadata.",
    )
    original_id: Series[str] = pa.Field(
        nullable=True,
        alias="_original_id",
        description="Original provider lookup identifier retained as lineage metadata.",
    )


__all__ = ["CompositeGoldCommonSchema", "CompositeLookupLineageSchema"]
