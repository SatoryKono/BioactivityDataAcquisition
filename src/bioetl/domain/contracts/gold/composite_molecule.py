# mypy: disable-error-code="misc"
"""Composite molecule Gold schema."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class CompositeMoleculeGoldSchema(pa.DataFrameModel):
    """Schema for Composite Molecule in Gold layer."""

    entity_id: Series[str] = pa.Field(
        nullable=False,
        description="Stable business identifier for merged molecule entity.",
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
        """Pandera configuration."""

        strict = False
        coerce = True
