# mypy: disable-error-code="misc"
"""Shared strict tail for Gold-layer Pandera contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class StrictGoldContractSchema(pa.DataFrameModel):
    """Common strict metadata and DQ fields for Gold contracts."""

    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


__all__ = ["StrictGoldContractSchema"]
