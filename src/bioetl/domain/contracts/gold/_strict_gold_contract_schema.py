# mypy: disable-error-code="misc"
"""Shared strict tail for Gold-layer Pandera contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class StrictGoldContractSchema(pa.DataFrameModel):
    """Common strict metadata and DQ fields for Gold contracts."""

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

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration for strict schema validation."""

        strict = True


__all__ = ["StrictGoldContractSchema"]
