# mypy: disable-error-code="misc"
"""Shared base schema for composite Gold-layer contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class CompositeGoldCommonSchema(pa.DataFrameModel):
    """Common composite Gold output fields across merged entity families."""

    entity_id: Series[str] = pa.Field(nullable=False)
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

        strict = False
        coerce = True


__all__ = ["CompositeGoldCommonSchema"]
