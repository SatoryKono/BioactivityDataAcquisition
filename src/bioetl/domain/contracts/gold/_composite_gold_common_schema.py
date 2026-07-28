# mypy: disable-error-code="misc"
# pyright: reportIncompatibleVariableOverride=false
# MRO/override residual on mixin or client hierarchies.
"""Shared base schema for composite Gold-layer contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._strict_gold_contract_schema import (
    StrictGoldContractSchema,
)


class CompositeGoldCommonSchema(StrictGoldContractSchema):
    """Common composite Gold output fields across merged entity families.

    Inherits strict Gold DQ/metadata tail from ``StrictGoldContractSchema``
    (ADR-018) so composite schemas participate in the uniform strict base.
    """

    entity_id: Series[str] = pa.Field(nullable=False)
    source: Series[str] = pa.Field(
        nullable=True,
        alias="_source",
        description="Source-family lineage marker retained as composite metadata.",
    )
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
        description=(
            "Lookup strategy retained as inherited provider/composite lineage metadata."
        ),
    )
    original_id: Series[str] = pa.Field(
        nullable=True,
        alias="_original_id",
        description="Original provider lookup identifier retained as lineage metadata.",
    )


__all__ = ["CompositeGoldCommonSchema", "CompositeLookupLineageSchema"]
